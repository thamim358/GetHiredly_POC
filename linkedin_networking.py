"""Browser-backed job discovery and reviewed LinkedIn invitations."""

from __future__ import annotations

import hashlib
import json
import logging
import queue
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    InvalidSessionIdException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

from job_networking import (
    NOTE_LIMIT, SearchSpec, draft_note, job_search_urls, people_search_urls, person_name,
    profile_match, location_matches, profile_url, read_resume_text, score_job, suggested_people_queries,
)


SENT_FILE = Path(__file__).with_name("network_invites.json")
LOGIN_EMAIL = "input#username, input[name='session_key'], input[type='email'][autocomplete^='username']"
LOGIN_PASSWORD = "input#password, input[name='session_password'], input[type='password']"


def _new_chrome_driver(options):
    """Start Chrome with one clean retry for transient ChromeDriver exits."""
    last_error = None
    for attempt in range(2):
        service = Service()
        try:
            return webdriver.Chrome(service=service, options=options)
        except WebDriverException as error:
            last_error = error
            try:
                service.stop()
            except Exception:
                pass
            if attempt == 0 and "unexpectedly exited" in str(error).casefold():
                time.sleep(1.0)
                continue
            break

    message = str(last_error).strip().replace("\r", " ").replace("\n", " ")
    if "3221225794" in message:
        message = (
            "ChromeDriver crashed while starting Chrome (Windows status 3221225794 / 0xC0000142). "
            "The app retried once. Close leftover automated Chrome windows and retry; no LinkedIn message was sent."
        )
    else:
        message = f"ChromeDriver could not start Chrome after a retry: {message[:240]}"
    raise RuntimeError(message) from last_error


def _profile_key(url: str) -> str:
    canonical = profile_url(str(url or ""))
    return canonical.casefold() if canonical else ""


def _visible(elements):
    for element in elements:
        try:
            if element.is_displayed() and element.is_enabled():
                return element
        except StaleElementReferenceException:
            continue
    return None


def _visible_matches(driver, by, selector: str):
    matches = []
    for element in driver.find_elements(by, selector):
        try:
            if element.is_displayed():
                matches.append(element)
        except StaleElementReferenceException:
            continue
    return matches


def _profile_slug(driver, profile_url_hint: str = "") -> str:
    canonical = profile_url(profile_url_hint or getattr(driver, "current_url", ""))
    return canonical.rstrip("/").rsplit("/", 1)[-1] if canonical else ""


def _profile_heading_text(driver, profile_url_hint: str = "") -> str:
    """Read the profile name in one DOM call, without passing stale elements back to Selenium."""
    slug = _profile_slug(driver, profile_url_hint)
    return driver.execute_script(
        """
        const slug = arguments[0];
        const norm = el => (el?.innerText || el?.textContent || '').replace(/\\s+/g, ' ').trim();
        const anchor = [...document.querySelectorAll('main a[href]')].find(a => {
          try { return new URL(a.href).pathname.replace(/\\/$/, '').toLowerCase() === ('/in/' + slug).toLowerCase(); }
          catch (_) { return false; }
        });
        const heading = anchor?.querySelector('h1, h2') ||
          [...document.querySelectorAll('[componentkey]')].find(e => e.getAttribute('componentkey') === 'ProfileVerificationTriggerRef-' + slug)?.querySelector('h1, h2') ||
          document.querySelector('[id$="Topcard"] h1, [id$="Topcard"] h2, main h1');
        return norm(heading);
        """,
        slug,
    ) or ""


def _note_send_controls(driver):
    """Return only Send actions for a personalized invite, never the no-note action."""
    selector = (
        "//*[@role='dialog']//button["
        "normalize-space(.)='Send' or normalize-space(.)='Send invitation' or "
        "@aria-label='Send' or @aria-label='Send invitation'] | "
        "//div[contains(@class,'artdeco-modal__actionbar')]//button["
        "normalize-space(.)='Send' or normalize-space(.)='Send invitation' or "
        "@aria-label='Send' or @aria-label='Send invitation']"
    )
    allowed = {"send", "send invitation"}
    controls = []
    for button in _visible_matches(driver, By.XPATH, selector):
        try:
            text = re.sub(r"\s+", " ", button.text or "").strip().casefold()
            label = re.sub(r"\s+", " ", button.get_attribute("aria-label") or "").strip().casefold()
            if text in allowed or label in allowed:
                controls.append(button)
        except StaleElementReferenceException:
            continue
    return controls


_PRONOUN_HEADLINE = re.compile(
    r"^(?:she|he|they|xe|ze|ey|ve|per|it)(?:\s*/\s*(?:she|her|hers|he|him|his|they|them|theirs|xe|xem|xyr|ze|zir|zem|ey|em|eir|ve|ver|vis|per|pers|it|its)){1,3}$",
    re.I,
)
_PROFILE_ACTION_LINE = re.compile(r"^(?:(?:[·•]\s*)?(?:1st|2nd|3rd)(?:\+)?|follow|connect|message|more|view profile)$", re.I)
_LOCATION_LINE = re.compile(
    r"^[^,]{2,80},\s*[^,]{2,80},\s*(?:United Kingdom|United States|India|Canada|Australia|New Zealand|Ireland|Scotland|England|UAE|United Arab Emirates)$",
    re.I,
)


def _select_profile_headline(candidates, name="") -> str:
    """Pick a visible headline candidate, ignoring pronouns and profile metadata."""
    for candidate in candidates or []:
        text = re.sub(r"\s+", " ", str(candidate or "")).strip()
        if not text or text.casefold() == str(name or "").strip().casefold():
            continue
        if _PRONOUN_HEADLINE.fullmatch(text) or _PROFILE_ACTION_LINE.fullmatch(text) or _LOCATION_LINE.fullmatch(text):
            continue
        return text
    return ""


def _button(driver, xpath: str, timeout: int = 8):
    return _wait_visible(driver, By.XPATH, xpath, timeout)


def _click_action(driver, by, selector: str, action: str, timeout: int = 8, transitioned=None):
    """Click a fresh LinkedIn control and confirm its expected UI transition."""
    last_error = None
    for attempt in range(2):
        try:
            element = _wait_visible(driver, by, selector, timeout if attempt == 0 else 4)
        except TimeoutException as error:
            raise RuntimeError(f"{action} is unavailable or disappeared before the click. No invitation was sent.") from error
        scroll = getattr(driver, "execute_script", None)
        if scroll:
            try:
                scroll("arguments[0].scrollIntoView({block:'center', inline:'center'});", element)
            except Exception:
                pass
        try:
            element.click()
        except (StaleElementReferenceException, ElementClickInterceptedException,
                ElementNotInteractableException) as error:
            last_error = error
        if transitioned is None:
            if last_error is None:
                return
        else:
            try:
                WebDriverWait(driver, timeout).until(transitioned)
                return
            except TimeoutException as error:
                last_error = error

        # Selenium can report a successful click even when LinkedIn's React UI
        # does not process it. Retry once with the currently rendered DOM node.
        if transitioned and transitioned(driver):
            return
        if "send" in action.casefold():
            raise RuntimeError(
                f"{action} did not produce confirmation. It was not clicked a second time to avoid a duplicate."
            ) from last_error
        fresh = _visible(driver.find_elements(by, selector))
        script = getattr(driver, "execute_script", None)
        if fresh and script:
            try:
                script("arguments[0].click();", fresh)
                if transitioned is None:
                    return
                WebDriverWait(driver, min(timeout, 8)).until(transitioned)
                return
            except Exception as script_error:
                last_error = script_error
            if attempt:
                break
    reason = f"LinkedIn did not complete the expected {action.lower()} transition"
    raise RuntimeError(f"{action} failed: {reason}. No invitation was sent.") from last_error


def _wait_visible(driver, by, selector: str, timeout: int = 8):
    return WebDriverWait(driver, timeout).until(lambda d: _visible(d.find_elements(by, selector)))


def _profile_connect_control(driver, expected_name: str):
    """Find Connect on the profile card even when LinkedIn moves it outside the heading tree."""
    slug = _profile_slug(driver)
    if not slug:
        return None
    return driver.execute_script(
        """
        const slug = arguments[0];
        const wanted = (arguments[1] || '').replace(/\\s+/g, ' ').trim().toLowerCase();
        const norm = value => (value || '').replace(/\\s+/g, ' ').trim().toLowerCase();
        const visible = el => {
          const style = getComputedStyle(el);
          return el.getClientRects().length && style.visibility !== 'hidden' && style.display !== 'none';
        };
        const exactInvite = [...document.querySelectorAll('button, a, [role="button"]')].filter(el => {
          if (!visible(el)) return false;
          const label = norm(el.getAttribute('aria-label'));
          return wanted && label.includes('invite') && label.includes(wanted) && label.includes('to connect');
        });
        if (exactInvite.length === 1) return exactInvite[0];
        const anchor = [...document.querySelectorAll('main a[href]')].find(a => {
          try { return new URL(a.href).pathname.replace(/\\/$/, '').toLowerCase() === ('/in/' + slug).toLowerCase(); }
          catch (_) { return false; }
        });
        const card = [...document.querySelectorAll('[componentkey]')].find(e => e.getAttribute('componentkey') === 'ProfileVerificationTriggerRef-' + slug)
          || [...document.querySelectorAll('[id$="Topcard"]')].find(e => (e.id || '').toLowerCase().includes(slug.toLowerCase()))
          || anchor?.closest('section, article, [componentkey]');
        const heading = card?.querySelector('h1, h2') || anchor?.querySelector('h1, h2');
        const matches = node => [...node.querySelectorAll('button, a, [role="button"]')].filter(el => {
          if (!visible(el)) return false;
          const text = norm(el.innerText || el.textContent);
          const label = norm(el.getAttribute('aria-label'));
          return text === 'connect' || label === 'connect';
        });
        for (let node = heading || card; node && node !== document.body; node = node.parentElement) {
          const controls = matches(node);
          if (controls.length === 1) return controls[0];
        }
        return null;
        """,
        slug,
        expected_name,
    )


def _profile_more_control(driver):
    """Find More inside the profile heading's card, avoiding other page menus."""
    slug = _profile_slug(driver)
    if not slug:
        return None
    return driver.execute_script(
        """
        const slug = arguments[0];
        const visible = el => {
          const style = getComputedStyle(el);
          return el.getClientRects().length && style.visibility !== 'hidden' && style.display !== 'none';
        };
        const anchor = [...document.querySelectorAll('main a[href]')].find(a => {
          try { return new URL(a.href).pathname.replace(/\\/$/, '').toLowerCase() === ('/in/' + slug).toLowerCase(); }
          catch (_) { return false; }
        });
        const heading = anchor?.querySelector('h1, h2') ||
          [...document.querySelectorAll('[componentkey]')].find(e => e.getAttribute('componentkey') === 'ProfileVerificationTriggerRef-' + slug)?.querySelector('h1, h2');
        if (!heading) return null;
        const isMore = el => {
          const text = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim().toLowerCase();
          const label = (el.getAttribute('aria-label') || '').toLowerCase();
          const title = (el.getAttribute('title') || '').toLowerCase();
          const icon = (el.innerHTML || '').toLowerCase();
          return text === 'more' || label.includes('more') || title.includes('more') ||
            ['ellipsis', 'overflow', 'three-dots', 'more-horizontal'].some(token => icon.includes(token));
        };
        for (let node = heading; node && node !== document.body; node = node.parentElement) {
          const controls = [...node.querySelectorAll('button, [role="button"]')].filter(el => visible(el) && isMore(el));
          if (controls.length === 1) return controls[0];
        }
        return null;
        """,
        slug,
    )


def _profile_message_control(driver, expected_name: str):
    """Find Message on the target profile card, including icon buttons without a compose href."""
    slug = _profile_slug(driver)
    if not slug:
        return None
    return driver.execute_script(
        """
        const slug = arguments[0];
        const wanted = (arguments[1] || '').replace(/\\s+/g, ' ').trim().toLowerCase();
        const norm = value => (value || '').replace(/\\s+/g, ' ').trim().toLowerCase();
        const visible = el => {
          const style = getComputedStyle(el);
          return el.getClientRects().length && style.visibility !== 'hidden' && style.display !== 'none';
        };
        const anchor = [...document.querySelectorAll('main a[href]')].find(a => {
          try { return new URL(a.href).pathname.replace(/\\/$/, '').toLowerCase() === ('/in/' + slug).toLowerCase(); }
          catch (_) { return false; }
        });
        const card = [...document.querySelectorAll('[componentkey]')].find(e => e.getAttribute('componentkey') === 'ProfileVerificationTriggerRef-' + slug)
          || [...document.querySelectorAll('[id$="Topcard"]')].find(e => wanted && (e.innerText || '').toLowerCase().includes(wanted))
          || anchor?.closest('section, article, [componentkey]');
        const heading = card?.querySelector('h1, h2') || anchor?.querySelector('h1, h2');
        const matches = node => [...node.querySelectorAll('a, button, [role="button"]')].filter(el => {
          if (!visible(el)) return false;
          const text = norm(el.innerText || el.textContent);
          const label = norm(el.getAttribute('aria-label'));
          const href = el.getAttribute('href') || '';
          return text === 'message' || label === 'message' || (wanted && label === ('message ' + wanted)) || href.includes('/messaging/compose/');
        });
        for (let node = heading || card; node && node !== document.body; node = node.parentElement) {
          const controls = matches(node);
          if (controls.length === 1) return controls[0];
          const named = controls.filter(el => norm(el.getAttribute('aria-label')) === ('message ' + wanted));
          if (named.length === 1) return named[0];
        }
        const named = [...document.querySelectorAll('a, button, [role="button"]')].filter(el =>
          visible(el) && wanted && norm(el.getAttribute('aria-label')) === ('message ' + wanted)
        );
        return named.length === 1 ? named[0] : null;
        """,
        slug,
        expected_name,
    )


def _menu_message_control(driver):
    """Find a Message action in the profile's open More menu."""
    return driver.execute_script(
        """
        const visible = el => {
          const style = getComputedStyle(el);
          return el.getClientRects().length && style.visibility !== 'hidden' && style.display !== 'none';
        };
        const matches = [...document.querySelectorAll('a, button, [role="menuitem"], [role="button"]')].filter(el => {
          if (!visible(el)) return false;
          const text = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim().toLowerCase();
          const label = (el.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim().toLowerCase();
          const inMenu = !!el.closest('[role="menu"], [role="menuitem"], [class*="dropdown"], [class*="popover"], [class*="menu"]');
          const composeLink = (el.href || '').includes('/messaging/compose/') && (text === 'message' || label === 'message');
          return composeLink || (inMenu && (text === 'message' || label === 'message'));
        });
        return matches.length === 1 ? matches[0] : null;
        """
    )


def _menu_connect_control(driver, expected_slug: str = ""):
    """Find a unique Connect action in LinkedIn's currently open profile menu."""
    return driver.execute_script(
        """
        const expected = (arguments[0] || '').toLowerCase();
        const visible = el => {
          const style = getComputedStyle(el);
          return el.getClientRects().length && style.visibility !== 'hidden' && style.display !== 'none';
        };
        const matches = [...document.querySelectorAll('a, button, [role="menuitem"], [role="button"]')].filter(el => {
          if (!visible(el)) return false;
          const text = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim().toLowerCase();
          const label = (el.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim().toLowerCase();
          const href = el.href || '';
          const inviteLink = href.includes('/preload/custom-invite/');
          let targetMatches = !expected;
          if (inviteLink && expected) {
            try { targetMatches = new URL(href).searchParams.get('vanityName')?.toLowerCase() === expected; }
            catch (_) { targetMatches = false; }
          }
          const inMenu = !!el.closest('[role="menu"], [role="menuitem"], [class*="dropdown"], [class*="popover"], [class*="menu"]');
          return (text === 'connect' || label === 'connect') && ((inviteLink && targetMatches) || inMenu);
        });
        return matches.length === 1 ? matches[0] : null;
        """,
        expected_slug,
    )


def _click_scoped_control(driver, get_control, action: str, transitioned, timeout: int = 20):
    """Click once, recovering from stale references only when the action did not transition."""
    not_sent = "No message was sent." if "message" in action.casefold() else "No invitation was sent."
    element = get_control()
    if not element:
        raise RuntimeError(f"Could not uniquely locate {action.lower()}. {not_sent}")
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", element)
        element.click()
    except (StaleElementReferenceException, ElementClickInterceptedException, ElementNotInteractableException):
        if transitioned(driver):
            return
        element = get_control()
        if not element:
            raise RuntimeError(f"{action} disappeared before it could be clicked. {not_sent}")
        try:
            driver.execute_script("arguments[0].click();", element)
        except (StaleElementReferenceException, ElementClickInterceptedException, ElementNotInteractableException):
            if transitioned(driver):
                return
            raise RuntimeError(f"{action} stayed blocked after re-query. {not_sent}")
    try:
        WebDriverWait(driver, timeout).until(transitioned)
        return
    except TimeoutException:
        if transitioned(driver):
            return
        raise RuntimeError(f"LinkedIn did not complete {action.lower()}. {not_sent}")


def _logged_in(driver) -> bool:
    return any(path in driver.current_url for path in ("/feed", "/jobs", "/mynetwork")) and not _visible(driver.find_elements(By.CSS_SELECTOR, LOGIN_EMAIL))


def sign_in(driver, credentials: dict) -> None:
    driver.get("https://www.linkedin.com/login")
    WebDriverWait(driver, 20).until(lambda d: _logged_in(d) or _visible(d.find_elements(By.CSS_SELECTOR, LOGIN_EMAIL)))
    if _logged_in(driver):
        return
    email = _visible(driver.find_elements(By.CSS_SELECTOR, LOGIN_EMAIL))
    password = _visible(driver.find_elements(By.CSS_SELECTOR, LOGIN_PASSWORD))
    if not email or not password:
        raise RuntimeError("LinkedIn sign-in fields were not found")
    email.clear()
    email.send_keys(credentials["email"])
    password.clear()
    password.send_keys(credentials["password"])
    _button(driver, "//button[normalize-space(.)='Sign in']", 15).click()
    try:
        WebDriverWait(driver, 120).until(_logged_in)
    except TimeoutException as error:
        raise RuntimeError("Complete LinkedIn verification in the browser, then search again") from error


class SendOutcomeUnknown(RuntimeError):
    """The Send action began, but LinkedIn did not confirm its result."""


def _send_direct_message(driver, candidate: dict, note: str, message_control) -> bool:
    """Send through Message only when Connect is unavailable; verify recipient and Premium gate."""
    editor_css = ".msg-form__contenteditable[contenteditable='true'][role='textbox'], [role='textbox'][contenteditable='true'][aria-label*='Write a message']"
    recipient_css = ".msg-compose__profile-link[href*='/in/'], .msg-inmail-compose-entity-lockup a[href*='/in/'], .msg-overlay-conversation-bubble__title"
    send_css = "button.msg-form__send-btn, form.msg-form button[type='submit']"

    def premium_gate(current_driver):
        for element in current_driver.find_elements(By.CSS_SELECTOR, "[role='dialog'], .artdeco-modal, .artdeco-modal__content"):
            try:
                if element.is_displayed() and re.search(
                    r"try premium|join premium|upgrade to premium|subscribe(?: to)? premium|start (?:your )?(?:free )?trial|premium (?:subscription )?required",
                    element.text or "", re.I,
                ):
                    return True
            except StaleElementReferenceException:
                continue
        return "/premium/" in str(getattr(current_driver, "current_url", "")).casefold()

    def composer_open(current_driver):
        return bool(_visible_matches(current_driver, By.CSS_SELECTOR, editor_css))

    def opened(current_driver):
        return composer_open(current_driver) or premium_gate(current_driver)

    if callable(message_control):
        _click_scoped_control(driver, message_control, "Open Message", opened, timeout=10)
    else:
        _click_action(driver, By.XPATH, "//main//a[contains(@href,'/messaging/compose/') and normalize-space(.)='Message']",
                      "Open Message", timeout=10, transitioned=opened)
    try:
        WebDriverWait(driver, 15).until(opened)
    except TimeoutException as error:
        raise RuntimeError("LinkedIn's Message composer did not open; no message was sent.") from error
    if premium_gate(driver):
        raise RuntimeError(
            "LinkedIn requires Premium to message this profile. No message was sent and no subscription option was selected."
        )

    try:
        recipient = _wait_visible(driver, By.CSS_SELECTOR, recipient_css, 8)
    except TimeoutException as error:
        raise RuntimeError("Message opened, but LinkedIn did not show a verifiable recipient; no message was sent.") from error
    href = recipient.get_attribute("href") or ""
    expected_name = person_name(candidate.get("name", ""))
    recipient_name = person_name(recipient.text)
    if href:
        recipient_url = urljoin(getattr(driver, "current_url", "https://www.linkedin.com/"), href)
        if _profile_key(recipient_url) != _profile_key(candidate.get("profileUrl", "")):
            raise RuntimeError("Message recipient does not match the reviewed profile; no message was sent.")
    elif not expected_name or not recipient_name:
        raise RuntimeError("Message recipient could not be verified; no message was sent.")
    if expected_name and recipient_name and expected_name.casefold() != recipient_name.casefold():
        raise RuntimeError("Message recipient name does not match the reviewed profile; no message was sent.")

    editor = _wait_visible(driver, By.CSS_SELECTOR, editor_css, 8)
    editor.click()
    editor.send_keys(Keys.CONTROL, "a")
    editor.send_keys(Keys.BACKSPACE)
    editor.send_keys(note)

    def text_of(element):
        return (element.get_attribute("innerText") or element.get_attribute("textContent") or element.text or "").strip()

    if re.sub(r"\s+", " ", text_of(editor)).strip() != re.sub(r"\s+", " ", note).strip():
        raise RuntimeError("The full reviewed message was not entered; no message was sent.")
    send = _wait_visible(driver, By.CSS_SELECTOR, send_css, 8)
    if not send.is_enabled():
        raise RuntimeError("LinkedIn's Message Send button is disabled; no message was sent.")

    def sent_or_cleared(current_driver):
        current = _visible_matches(current_driver, By.CSS_SELECTOR, editor_css)
        return not current or re.sub(r"\s+", " ", text_of(current[0])).strip() != re.sub(r"\s+", " ", note).strip()

    try:
        _click_action(driver, By.CSS_SELECTOR, send_css, "Send reviewed LinkedIn message", 8, sent_or_cleared)
        WebDriverWait(driver, 12).until(sent_or_cleared)
    except Exception as error:
        raise SendOutcomeUnknown(
            "LinkedIn did not confirm the direct message. Check the conversation before retrying to avoid a duplicate."
        ) from error
    candidate["deliveryMethod"] = "direct_message"
    return True


def _session_was_lost(error: Exception) -> bool:
    text = str(error).casefold()
    return isinstance(error, InvalidSessionIdException) or any(
        marker in text for marker in (
            "invalid session id", "session deleted", "browser has closed the connection",
            "chrome not reachable", "disconnected: not connected to devtools",
        )
    )


def send_connection_note(driver, candidate: dict, note: str) -> bool:
    """Use fresh locators after each LinkedIn UI transition to send one note."""
    target = profile_url(candidate.get("profileUrl", ""))
    if not target:
        raise ValueError("Candidate profile URL is invalid")
    note = note.strip()
    if not note or len(note) > NOTE_LIMIT:
        raise ValueError(f"Connection note must be 1–{NOTE_LIMIT} characters")
    driver.get(target)
    _wait_visible(driver, By.XPATH, "//main", 20)

    # Never keep a main/top-card element across a click: LinkedIn replaces
    # these nodes during Follow, Connect, and invitation-dialog updates.
    heading_name = person_name(_profile_heading_text(driver, target))
    expected_name = person_name(candidate.get("name", ""))
    if heading_name and expected_name and heading_name.casefold() != expected_name.casefold():
        raise RuntimeError("The profile name differs from the reviewed candidate; no invitation was sent")

    textarea_css = (
        "textarea#custom-message, "
        "[role='dialog'] textarea[name='message'], "
        "textarea.connect-button-send-invite__custom-message"
    )
    add_note_css = (
        "[role='dialog'] button[aria-label='Add a note'], "
        ".artdeco-modal__actionbar button[aria-label='Add a note']"
    )
    modal_css = add_note_css + ", " + textarea_css
    def invitation_surface_open(current_driver):
        return bool(
            _visible_matches(current_driver, By.CSS_SELECTOR, modal_css)
        )

    # Networking outreach only uses Connect with a reviewed invitation note.
    candidate["deliveryMethod"] = "connection_note"
    invite_route_opened = False
    if not invitation_surface_open(driver):
        expected_profile_name = heading_name or candidate.get("name", "")
        get_profile_connect = lambda: _profile_connect_control(driver, expected_profile_name)
        connect = get_profile_connect()
        if not connect:
            get_profile_more = lambda: _profile_more_control(driver)
            if get_profile_more():
                try:
                    _click_scoped_control(
                        driver, get_profile_more, "Open profile actions",
                        lambda d: _menu_connect_control(d, _profile_slug(d)) is not None, timeout=8,
                    )
                except RuntimeError as error:
                    raise RuntimeError(f"{error} No profile invitation was sent.") from error
                get_profile_connect = lambda: _menu_connect_control(driver, _profile_slug(driver))
                connect = get_profile_connect()
        if not connect:
            get_menu_message = lambda: _menu_message_control(driver)
            message = get_menu_message()
            get_profile_message = lambda: _profile_message_control(driver, expected_profile_name)
            if not message:
                message = get_profile_message()
            if message:
                candidate["deliveryMethod"] = "direct_message"
                message_locator = get_menu_message if get_menu_message() else get_profile_message
                return _send_direct_message(driver, candidate, note, message_locator)
            raise RuntimeError(
                "This profile has no usable Connect or Message action. "
                "No other profile's control was clicked; no outreach was sent."
            )
        candidate["deliveryMethod"] = "connection_note"
        label = connect.get_attribute("aria-label") or ""
        if label.startswith("Invite "):
            invited = person_name(label.removeprefix("Invite ").removesuffix(" to connect"))
            if heading_name and invited.casefold() != heading_name.casefold():
                raise RuntimeError("Connect belongs to a different profile; no note was sent")
        # LinkedIn's current More > Connect entry is a /preload/custom-invite/
        # anchor. Navigating to that exact, profile-scoped route loads the same
        # invitation dialog reliably; clicking it can leave a blank dialog shell.
        connect_href = connect.get_attribute("href") or ""
        invite_url = urljoin(getattr(driver, "current_url", target), connect_href)
        if invite_url.startswith("https://www.linkedin.com/preload/custom-invite/"):
            driver.get(invite_url)
            invite_route_opened = True
        try:
            if not invite_route_opened:
                _click_scoped_control(
                    driver, get_profile_connect, "Open Connect invitation",
                    invitation_surface_open, timeout=20,
                )
        except RuntimeError as error:
            visible_modals = sum(
                1 for element in driver.find_elements(By.CSS_SELECTOR, "[role='dialog'], .artdeco-modal")
                if element.is_displayed()
            )
            visible_connects = sum(
                1 for element in driver.find_elements(By.XPATH, "//main//*[self::button or self::a][normalize-space(.)='Connect']")
                if element.is_displayed()
            )
            visible_add_note = sum(
                1 for element in driver.find_elements(By.CSS_SELECTOR, add_note_css)
                if element.is_displayed()
            )
            raise RuntimeError(
                f"{error} LinkedIn state after click: {visible_modals} invitation modals, "
                f"{visible_connects} profile Connect controls, {visible_add_note} Add a note buttons. "
                "Check whether LinkedIn shows a restriction or an existing connection."
            ) from error

    try:
        WebDriverWait(driver, 10).until(invitation_surface_open)
    except TimeoutException as error:
        raise RuntimeError("The Connect dialog did not open. No note was sent.") from error
    if not _visible_matches(driver, By.CSS_SELECTOR, textarea_css):
        add_note_buttons = _visible_matches(driver, By.CSS_SELECTOR, add_note_css)
        if len(add_note_buttons) != 1:
            raise RuntimeError(
                f"Expected one Add a note button in the invitation modal, found {len(add_note_buttons)}. "
                "No other page button was clicked; no invitation was sent."
            )
        try:
            _click_action(
                driver, By.CSS_SELECTOR, add_note_css, "Open Add a note", timeout=10,
                transitioned=lambda d: bool(_visible_matches(d, By.CSS_SELECTOR, textarea_css)),
            )
        except RuntimeError as error:
            # The button may disappear because React replaced it with the editor.
            # Confirm that transition before reporting a failed click.
            if not _visible_matches(driver, By.CSS_SELECTOR, textarea_css):
                raise RuntimeError(f"{error} The invitation note editor did not open.") from error

    try:
        textareas = _visible_matches(driver, By.CSS_SELECTOR, textarea_css)
        if len(textareas) != 1:
            textarea = _wait_visible(driver, By.CSS_SELECTOR, textarea_css, 10)
        else:
            textarea = textareas[0]
    except TimeoutException as error:
        raise RuntimeError(
            "LinkedIn did not show the note field after Add a note. The ‘Send without a note’ action was not used."
        ) from error
    for attempt in range(2):
        try:
            textarea.clear()
            textarea.send_keys(note)
            break
        except StaleElementReferenceException:
            if attempt:
                raise RuntimeError("LinkedIn kept refreshing the note editor; the note was not sent")
            textarea = _wait_visible(driver, By.CSS_SELECTOR, textarea_css, 5)
    try:
        entered = (textarea.get_attribute("value") or textarea.text).strip()
    except StaleElementReferenceException:
        textarea = _wait_visible(driver, By.CSS_SELECTOR, textarea_css, 5)
        entered = (textarea.get_attribute("value") or textarea.text).strip()
    if entered != note:
        raise RuntimeError("The full connection note was not entered")

    send_buttons = _note_send_controls(driver)
    if len(send_buttons) != 1:
        raise RuntimeError(
            f"Expected one Send button for the personalized note, found {len(send_buttons)}; "
            "the separate 'Send without a note' action was not selected."
        )
    send = send_buttons[0]
    if not send.is_enabled():
        raise RuntimeError("The note is filled, but LinkedIn has not enabled Send; no note was sent.")
    send_click_error = None
    send_xpath = (
        "//*[@role='dialog']//button["
        "normalize-space(.)='Send' or normalize-space(.)='Send invitation' or "
        "@aria-label='Send' or @aria-label='Send invitation'] | "
        "//div[contains(@class,'artdeco-modal__actionbar')]//button["
        "normalize-space(.)='Send' or normalize-space(.)='Send invitation' or "
        "@aria-label='Send' or @aria-label='Send invitation']"
    )
    try:
        _click_action(driver, By.XPATH, send_xpath, "Send reviewed note", 5,
                      transitioned=lambda d: not _visible(d.find_elements(By.CSS_SELECTOR, textarea_css)))
    except RuntimeError as error:
        send_click_error = error
    try:
        WebDriverWait(driver, 10).until(lambda d: not _visible(d.find_elements(By.CSS_SELECTOR, textarea_css)))
    except Exception as error:
        # Never click Send a second time when the first click's outcome is unclear.
        raise SendOutcomeUnknown(
            "LinkedIn did not confirm this send. Check the profile's invitation state before retrying to avoid a duplicate."
        ) from (send_click_error or error)
    if send_click_error:
        logging.info("Send click raised after the note editor closed; treating the invitation as confirmed")
    return True


class NetworkingAssistant:
    def __init__(self):
        self._lock = threading.RLock()
        self._queue = queue.Queue()
        self._stop = threading.Event()
        self._thread = None
        self._last_profile_scan = {"discovered": 0, "checked": 0, "qualified": 0}
        self._state = {"status": "idle", "message": "", "jobs": [], "people": [], "searchTerms": [],
                       "profileScan": {"discovered": 0, "checked": 0, "qualified": 0}, "lastProfileCheck": {}}

    def state(self) -> dict:
        with self._lock:
            return json.loads(json.dumps(self._state))

    def _set(self, **changes):
        with self._lock:
            self._state.update(changes)

    def start(self, payload: dict, credentials: dict):
        spec = SearchSpec.from_payload(payload)
        if spec.resume:
            read_resume_text(spec.resume)  # Validate before starting a browser.
        if not credentials.get("email") or not credentials.get("password"):
            raise ValueError("Enter LinkedIn credentials in the LinkedIn tab")
        with self._lock:
            if self._thread and self._thread.is_alive():
                raise ValueError("A networking search is already active")
            self._queue = queue.Queue()
            self._stop.clear()
            self._state = {
                "status": "searching", "message": "Opening LinkedIn...", "jobs": [], "people": [],
                "searchTerms": suggested_people_queries(spec),
                "profileScan": {"discovered": 0, "checked": 0, "qualified": 0},
                "lastProfileCheck": {},
            }
            self._thread = threading.Thread(target=self._run, args=(spec, credentials), daemon=True)
            self._thread.start()
        return self.state()

    def send(self, candidate_id: str, note: str):
        note = str(note).strip()
        if not note or len(note) > NOTE_LIMIT:
            raise ValueError(f"Connection note must be 1–{NOTE_LIMIT} characters")
        with self._lock:
            if self._state["status"] != "ready":
                raise ValueError("Finish the search before sending a note")
            candidate = next((p for p in self._state["people"] if p["id"] == candidate_id), None)
            if not candidate:
                raise ValueError("Choose a discovered profile")
            if candidate.get("status") not in {"draft", "error"}:
                raise ValueError("This invitation is already queued or sent")
            key = _profile_key(candidate.get("profileUrl", ""))
            if key in self._sent_profiles() or any(
                other is not candidate and _profile_key(other.get("profileUrl", "")) == key
                and other.get("status") in {"queued", "sending", "sent", "uncertain", "duplicate"}
                for other in self._state["people"]
            ):
                candidate["status"] = "duplicate"
                candidate["error"] = "This profile already has a send attempt; skipped to prevent a duplicate."
                raise ValueError("A note was already sent or queued for this person")
            candidate["status"] = "queued"
            candidate["note"] = note
        self._queue.put((candidate_id, note))
        return self.state()

    def send_all(self, notes: dict[str, str]):
        """Queue every checked draft in order for a dedicated sender browser."""
        if not isinstance(notes, dict):
            raise ValueError("Reviewed notes must be provided as an object")
        with self._lock:
            if self._state["status"] != "ready":
                raise ValueError("Finish the people search before starting the sender browser")
            candidates = [p for p in self._state["people"] if p.get("status") in {"draft", "error"}]
            if not candidates:
                raise ValueError("There are no unsent profile notes to queue")
            history = self._invite_history()
            seen = set()
            pending = []
            skipped = []
            for person in candidates:
                key = _profile_key(person.get("profileUrl", ""))
                prior = history.get(key)
                if prior or key in seen:
                    prior_status = prior.get("status", "sent") if isinstance(prior, dict) else "sent"
                    skipped.append((person, "uncertain" if prior_status in {"attempting", "uncertain"} else
                                    ("sent" if prior else "duplicate")))
                    continue
                seen.add(key)
                note = str(notes.get(person["id"], person.get("note", ""))).strip()
                if not note or len(note) > NOTE_LIMIT:
                    raise ValueError(f"Check the note for {person.get('name') or 'a profile'}; use 1–{NOTE_LIMIT} characters")
                pending.append((person, note))
            for person, status in skipped:
                person["status"] = status
                person["error"] = "Skipped because this profile was already sent, attempted, or queued in this batch."
            if not pending:
                self._state["message"] = "No new notes to send; duplicate profiles were skipped."
                return self.state()
            for person, note in pending:
                person["status"] = "queued"
                person["note"] = note
            self._state["message"] = f"Queued {len(pending)} reviewed notes. Sending one profile at a time..."
            for person, note in pending:
                self._queue.put((person["id"], note))
        return self.state()

    def stop(self):
        if not self._thread or not self._thread.is_alive():
            self._set(status="idle", message="Networking browser is closed")
            return
        self._stop.set()
        self._queue.put(None)
        self._set(status="stopping", message="Closing networking browser...")

    def _run(self, spec: SearchSpec, credentials: dict):
        search_driver = None
        sender_driver = None
        try:
            options = Options()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            search_driver = _new_chrome_driver(options)
            sign_in(search_driver, credentials)
            resume_text = read_resume_text(spec.resume)
            jobs = self._find_jobs(search_driver, spec, resume_text)
            self._set(jobs=jobs, message="Searching LinkedIn for profiles...")
            people = self._find_people(search_driver, spec)
            invite_history = self._invite_history()
            for person in people:
                prior = invite_history.get(_profile_key(person.get("profileUrl", "")))
                if prior:
                    status = prior.get("status", "sent") if isinstance(prior, dict) else "sent"
                    person["status"] = "uncertain" if status in {"attempting", "uncertain"} else "sent"
                    if person["status"] == "uncertain":
                        person["error"] = "A previous send attempt may have reached LinkedIn; skipped to prevent a duplicate."
            scan = self._last_profile_scan
            if not scan["discovered"]:
                message = "LinkedIn returned no accessible profile links for these searches. Try different locations or search terms."
            elif not people:
                message = f"Checked {scan['checked']} profiles; none matched this mode's profile rule."
            else:
                message = f"Found {len(jobs)} jobs and {len(people)} people after checking {scan['checked']} profiles. Review each note before sending."
            search_driver.quit()
            search_driver = None
            self._set(people=people, status="ready", message=message + " Search browser closed; the separate sender browser opens when you start the batch.")

            while not self._stop.is_set():
                try:
                    item = self._queue.get(timeout=2)
                except queue.Empty:
                    continue
                if item is None:
                    break
                candidate_id, note = item
                with self._lock:
                    person = next((p for p in self._state["people"] if p["id"] == candidate_id), None)
                    if person:
                        person["status"] = "sending"
                        self._state["message"] = f"Sending note to {person.get('name') or 'profile'}..."
                if not person:
                    continue
                send_confirmed = False
                try:
                    if sender_driver is None:
                        sender_options = Options()
                        sender_options.add_argument("--start-maximized")
                        sender_options.add_argument("--disable-blink-features=AutomationControlled")
                        sender_driver = _new_chrome_driver(sender_options)
                        try:
                            sign_in(sender_driver, credentials)
                        except Exception:
                            sender_driver.quit()
                            sender_driver = None
                            raise
                    profile_key = _profile_key(person.get("profileUrl", ""))
                    if profile_key in self._sent_profiles():
                        with self._lock:
                            person["status"] = "duplicate"
                            person["error"] = "A prior send attempt exists; skipped to prevent a duplicate."
                        continue
                    self._record_attempt(person, note)
                    send_connection_note(sender_driver, person, note)
                    send_confirmed = True
                    self._record_sent(person, note)
                    with self._lock:
                        person["status"] = "sent"
                        person.pop("error", None)
                except Exception as error:
                    logging.exception("Could not send connection invitation")
                    session_lost = _session_was_lost(error)
                    if isinstance(error, SendOutcomeUnknown) or send_confirmed or session_lost:
                        self._record_uncertain(person, note)
                    else:
                        self._clear_attempt(person)
                    error_lines = str(error).strip().splitlines()
                    error_message = error_lines[0][:200] if error_lines and error_lines[0].strip() else (
                        f"{type(error).__name__}: LinkedIn did not complete this action."
                    )
                    with self._lock:
                        person["status"] = "uncertain" if isinstance(error, SendOutcomeUnknown) else "error"
                        person["error"] = error_message
                    if session_lost:
                        # Never reuse a dead WebDriver session. The current invite
                        # is uncertain because the browser may have closed after
                        # LinkedIn accepted it; remaining batch items did not run.
                        if sender_driver:
                            try:
                                sender_driver.quit()
                            except Exception:
                                pass
                            sender_driver = None
                        person["status"] = "uncertain"
                        person["error"] = (
                            "The LinkedIn sending browser closed during this attempt. Delivery is uncertain; "
                            "check this profile on LinkedIn before retrying."
                        )
                    if sender_driver is None:
                        # A failed sender-browser startup/login affects every item
                        # already in this batch. Mark them all and drain the queue.
                        reason = (
                            "LinkedIn sender browser closed unexpectedly; this queued note was not attempted. "
                            "Retry it after opening a fresh sending batch."
                            if session_lost else
                            f"Sender browser could not start or sign in: {error_message[:160]}"
                        )
                        with self._lock:
                            for queued_person in self._state["people"]:
                                if queued_person.get("status") == "queued":
                                    queued_person["status"] = "error"
                                    queued_person["error"] = reason
                            self._state["message"] = reason
                        while True:
                            try:
                                if self._queue.get_nowait() is None:
                                    self._queue.put(None)
                                    break
                            except queue.Empty:
                                break
        except Exception as error:
            logging.exception("Networking search failed")
            self._set(status="error", message=str(error).splitlines()[0][:250])
        finally:
            if search_driver:
                try:
                    search_driver.quit()
                except Exception:
                    pass
            if sender_driver:
                try:
                    sender_driver.quit()
                except Exception:
                    pass
            if self._stop.is_set():
                self._set(status="idle", message="Networking browser closed")

    def _find_jobs(self, driver, spec: SearchSpec, resume_text: str) -> list[dict]:
        jobs = {}
        for url in job_search_urls(spec):
            if self._stop.is_set():
                break
            driver.get(url)
            try:
                WebDriverWait(driver, 12).until(lambda d: d.find_elements(By.CSS_SELECTOR, "a[href*='/jobs/view/']"))
            except TimeoutException:
                continue
            for scroll_index in range(3):
                cards = driver.execute_script("""
                    return [...document.querySelectorAll('a[href*="/jobs/view/"]')].map(a => {
                      let card = a.parentElement;
                      for (let parent = card?.parentElement, depth = 0; parent && depth < 8; parent = parent.parentElement, depth++) {
                        if (parent.querySelectorAll('a[href*="/jobs/view/"]').length !== 1) break;
                        if ((parent.innerText || '').length > 1200) break;
                        card = parent;
                      }
                      const text = (sel) => card?.querySelector(sel)?.innerText?.trim() || '';
                      const lines = (card?.innerText || '').split('\\n').map(x => x.trim()).filter(Boolean);
                      const rawLocation = text('.job-card-container__metadata-item, .artdeco-entity-lockup__caption, .job-search-card__location')
                        || lines.find(x => /remote|hybrid|dubai|united arab emirates|india|riyadh|qatar|saudi|on.site/i.test(x))
                        || (lines.length >= 3 ? lines[2] : '');
                      const location = rawLocation.split(/[\\u00b7\\u2022\\n]/)[0].trim();
                      const timeText = text('time, .job-card-container__footer-item')
                        || lines.find(x => /\\b(?:minute|hour|day|week)s? ago|reposted/i.test(x)) || '';
                      const posted = (timeText.match(/\\b\\d+\\s+(?:minute|hour|day|week)s? ago/i) || [])[0] || '';
                      return {url:a.href.split('?')[0], title:a.innerText.trim() || text('.job-card-list__title'),
                        company:text('.job-card-container__primary-description, .artdeco-entity-lockup__subtitle, .job-search-card__subtitle') || lines[1] || '',
                        location, posted, description:card?.innerText?.slice(0,600) || ''};
                    }).filter(x => x.url && x.title);
                """) or []
                for job in cards:
                    if not location_matches(job.get("location", ""), spec):
                        continue
                    key = re.search(r"/jobs/view/(\d+)", job["url"])
                    key = key.group(1) if key else job["url"]
                    if key in jobs:
                        continue
                    score, reasons = score_job(job, spec, resume_text)
                    job.update(id=key, score=score, reasons=reasons)
                    jobs[key] = job
                if len(jobs) >= 30:
                    break
                if scroll_index < 2:
                    driver.execute_script("const m=document.querySelector('main'); if(m) m.scrollTop += 900; window.scrollBy(0,900);")
                    time.sleep(1)
        return sorted(jobs.values(), key=lambda item: item["score"], reverse=True)[:30]

    def _find_people(self, driver, spec: SearchSpec) -> list[dict]:
        discovered = {}
        checked = 0
        for url in people_search_urls(spec):
            if self._stop.is_set() or len(discovered) >= 36:
                break
            driver.get(url)
            try:
                WebDriverWait(driver, 6).until(lambda d: d.find_elements(By.CSS_SELECTOR, "a[href*='/in/']"))
            except TimeoutException:
                continue
            for _ in range(2):
                driver.execute_script("window.scrollBy(0,700)")
                time.sleep(0.5)
            rows = driver.execute_script("""
                const main = document.querySelector('main');
                let anchors = [...(main || document).querySelectorAll("a[href*='/in/']")];
                if (!anchors.length) anchors = [...document.querySelectorAll("a[href*='/in/']")];
                return anchors.filter(a => !a.closest('nav,header')).map(a => {
                  const row = a.closest('li,[role="listitem"]') || a.parentElement?.parentElement || a.parentElement;
                  return {profileUrl:a.href, label:a.getAttribute('aria-label') || a.getAttribute('title') || a.innerText || a.querySelector('img')?.alt || '',
                    preview:(row?.innerText || '').slice(0,500)};
                });
            """) or []
            for row in rows:
                profile = profile_url(row.get("profileUrl", ""))
                if profile and profile not in discovered:
                    discovered[profile] = row
            self._set(
                profileScan={"discovered": len(discovered), "checked": checked, "qualified": 0},
                message=f"Found {len(discovered)} profile links. Checking profiles against the selected mode...",
            )

        people = []
        profile_results = list(discovered.items())[:36]
        for profile, result in profile_results:
            if self._stop.is_set() or len(people) >= 20:
                break
            try:
                checked += 1
                self._set(
                    profileScan={"discovered": len(discovered), "checked": checked, "qualified": len(people)},
                    message=f"Checking profile {checked} of {len(profile_results)}; {len(people)} matched so far...",
                )
                driver.get(profile)
                try:
                    WebDriverWait(driver, 10).until(lambda d: _visible(d.find_elements(
                        By.CSS_SELECTOR,
                        "[id$='Topcard'] p, [id$='Topcard'] h1, .pv-top-card p, .pv-top-card h1, main p, main h1, h1",
                    )))
                except TimeoutException:
                    # LinkedIn may render the profile headline as a generated-class
                    # paragraph and omit a semantic h1. Still inspect the page and
                    # fall back to the search-result card headline below.
                    pass
                snapshot = driver.execute_script("""
                    const main = document.querySelector('main') || document.body;
                    const top = document.querySelector("[id^='com.linkedin.sdui.profile.card.'][id$='Topcard']")
                      || document.querySelector("[id$='Topcard']")
                      || document.querySelector("[data-view-name*='profile-card']")
                      || document.querySelector('.pv-top-card') || null;
                    const heading = main.querySelector('h1') || document.querySelector('h1');
                    let header = top;
                    if (!header && heading) {
                      header = heading;
                      for (let i = 0; i < 8 && header && !header.querySelector('p'); i++) header = header.parentElement;
                    }
                    header = header || main;
                    const name = header.querySelector('h1')?.innerText?.trim() || heading?.innerText?.trim() || '';
                    const semanticHeadline = [...header.querySelectorAll('[class*="headline"], .pv-text-details__left-panel .text-body-medium.break-words')]
                      .map(node => node.innerText?.trim()).filter(Boolean);
                    const paras = [...header.querySelectorAll('p')].map(node => node.innerText?.trim()).filter(Boolean);
                    const lines = (header.innerText || '').split(/\\n+/).map(x => x.trim()).filter(Boolean);
                    return {name, headlineCandidates:[...semanticHeadline, ...paras, ...lines]};
                """) or {}
                name = person_name(snapshot.get("name", "")) or person_name(result.get("label", ""))
                preview = result.get("preview", "")
                candidates = list(snapshot.get("headlineCandidates", []) or [])
                if snapshot.get("headline"):
                    candidates.insert(0, snapshot.get("headline"))
                headline = _select_profile_headline(candidates, name)
                if not headline:
                    preview_lines = [re.sub(r"\s+", " ", line).strip() for line in re.split(r"[\r\n]+", preview) if line.strip()]
                    headline = _select_profile_headline(preview_lines, name)
                # Hiring mode intentionally checks only the displayed headline.
                # Preview, About, location, and experience text must not gate a profile.
                matched, terms, reason = profile_match(headline, spec)
                self._set(lastProfileCheck={
                    "name": name, "headline": headline, "matched": matched,
                    "reason": reason, "profileUrl": profile,
                })
                if not matched:
                    continue
                matched_term = terms[0]
                topic = "hiring role" if spec.search_mode == "hiring_managers" else f"experience with {matched_term}"
                identifier = hashlib.sha256(profile.encode()).hexdigest()[:16]
                people.append({
                    "id": identifier, "name": name, "headline": headline, "company": "",
                    "profileUrl": profile, "postUrl": "", "topic": topic,
                    "matchedTerms": terms, "matchReason": reason, "searchMode": spec.search_mode,
                    "excerpt": (result.get("preview", "") or headline)[:300],
                    "note": draft_note(name, topic, spec.titles[0], mode=spec.search_mode, matched_term=matched_term),
                    "status": "draft",
                })
                self._set(
                    people=list(people),
                    profileScan={"discovered": len(discovered), "checked": checked, "qualified": len(people)},
                    message=f"Checked {checked} profiles; {len(people)} matched. Continuing profile scan...",
                )
            except Exception as error:
                preview_lines = [re.sub(r"\s+", " ", line).strip() for line in
                                 re.split(r"[\r\n]+", result.get("preview", "")) if line.strip()]
                preview_headline = _select_profile_headline(preview_lines, person_name(result.get("label", "")))
                message = f"Could not read profile headline ({type(error).__name__})"
                logging.info("Profile check failed: %s: %s", type(error).__name__, str(error).splitlines()[0][:160])
                self._set(lastProfileCheck={
                    "name": person_name(result.get("label", "")), "headline": preview_headline,
                    "matched": False, "reason": message, "profileUrl": profile,
                })
        self._last_profile_scan = {"discovered": len(discovered), "checked": checked, "qualified": len(people)}
        self._set(people=list(people), profileScan=dict(self._last_profile_scan))
        return people

    @staticmethod
    def _invite_history() -> dict[str, dict]:
        try:
            data = json.loads(SENT_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        entries = {}
        if isinstance(data, dict):
            rows = data.items()
        elif isinstance(data, list):
            rows = ((url, {"status": "sent"}) for url in data)
        else:
            return {}
        for url, record in rows:
            key = _profile_key(url)
            if key:
                entries[key] = record if isinstance(record, dict) else {"status": "sent"}
        return entries

    @classmethod
    def _sent_profiles(cls) -> set[str]:
        return set(cls._invite_history())

    @staticmethod
    def _write_invite_history(history: dict[str, dict]):
        SENT_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

    def _record_attempt(self, person: dict, note: str):
        history = self._invite_history()
        key = _profile_key(person.get("profileUrl", ""))
        if not key:
            raise ValueError("Candidate profile URL is invalid")
        history[key] = {
            "name": person.get("name", ""), "note": note, "status": "attempting",
            "attemptedAt": datetime.now().isoformat(),
        }
        self._write_invite_history(history)

    def _record_uncertain(self, person: dict, note: str):
        history = self._invite_history()
        key = _profile_key(person.get("profileUrl", ""))
        if not key:
            return
        prior = history.get(key, {})
        history[key] = {
            **prior, "name": person.get("name", ""), "note": note, "status": "uncertain",
            "updatedAt": datetime.now().isoformat(),
        }
        self._write_invite_history(history)

    def _clear_attempt(self, person: dict):
        key = _profile_key(person.get("profileUrl", ""))
        history = self._invite_history()
        prior = history.get(key, {})
        if isinstance(prior, dict) and prior.get("status") == "attempting":
            history.pop(key, None)
            self._write_invite_history(history)

    def _record_sent(self, person: dict, note: str):
        history = self._invite_history()
        key = _profile_key(person.get("profileUrl", ""))
        if not key:
            raise ValueError("Candidate profile URL is invalid")
        history[key] = {
            "name": person.get("name", ""), "note": note, "status": "sent",
            "sentAt": datetime.now().isoformat(),
        }
        self._write_invite_history(history)
