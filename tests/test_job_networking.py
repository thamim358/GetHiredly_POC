import unittest
import threading
import time
import tempfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from selenium.common.exceptions import InvalidSessionIdException, StaleElementReferenceException, TimeoutException, WebDriverException

from job_networking import SearchSpec, draft_note, job_search_urls, location_matches, people_search_urls, person_name, post_search_urls, post_topic, profile_match, profile_url, score_job, suggested_people_queries
from linkedin_networking import NetworkingAssistant, _new_chrome_driver, _profile_key, _select_profile_headline, _send_direct_message, send_connection_note
from professional_dashboard_api import app, merge_linkedin_credentials


class JobNetworkingTests(unittest.TestCase):
    def setUp(self):
        self.spec = SearchSpec(
            locations=['Dubai'], titles=['Playwright Automation Engineer'],
            alternate_titles=['SDET'], skills=['Playwright', 'TypeScript'],
            work_mode='remote', hiring_text='Hiring QA engineers for CMS automation',
            resume='uploads/example.pdf',
        )

    def test_recent_search_and_recruiter_queries(self):
        self.assertIn('f_TPR=r604800', job_search_urls(self.spec)[0])
        self.assertIn('location=Dubai', job_search_urls(self.spec)[0])
        self.assertIn('past-week', post_search_urls(self.spec)[0])
        queries = suggested_people_queries(self.spec)
        self.assertTrue(any('recruiter' in query and 'Dubai' in query for query in queries))
        self.assertTrue(any('hiring manager' in query for query in queries))

    def test_chrome_driver_startup_retries_and_reports_windows_crash_clearly(self):
        driver = object()
        transient = WebDriverException(
            'Service chromedriver unexpectedly exited. Status code was: 3221225794'
        )
        with patch('linkedin_networking.webdriver.Chrome', side_effect=[transient, driver]) as chrome, \
             patch('linkedin_networking.time.sleep'):
            self.assertIs(_new_chrome_driver(object()), driver)
        self.assertEqual(chrome.call_count, 2)

        with patch('linkedin_networking.webdriver.Chrome', side_effect=transient), \
             patch('linkedin_networking.time.sleep'):
            with self.assertRaisesRegex(RuntimeError, 'Windows status 3221225794.*retried once'):
                _new_chrome_driver(object())

    def test_profile_mode_rules_and_mode_specific_queries(self):
        is_hiring, terms, _ = profile_match('Senior Talent Acquisition Partner', self.spec)
        self.assertTrue(is_hiring)
        self.assertEqual(terms, ['talent acquisition'])
        self.assertFalse(profile_match('Playwright Automation Engineer', self.spec)[0])

        referral_spec = replace(self.spec, search_mode='referral_contacts')
        is_referral, terms, _ = profile_match('Playwright Automation Engineer', referral_spec)
        self.assertTrue(is_referral)
        self.assertIn('playwright', terms)
        self.assertTrue(profile_match('Automation Lead', referral_spec)[0])
        self.assertIn('automation', profile_match('Automation Lead', referral_spec)[1])
        self.assertFalse(profile_match('Talent Acquisition Partner', referral_spec)[0])
        self.assertIn('recruiter', people_search_urls(self.spec)[0])
        self.assertIn('Playwright', people_search_urls(referral_spec)[0])

    def test_hiring_profile_terms_include_related_roles_but_reject_generic_words(self):
        hiring_profiles = [
            'IT Recruiter', 'Recruiting Manager', 'Human Resource Business Partner',
            'HRBP', 'Talent Acquisition Specialist', 'Talent Sourcer',
            'People Operations Manager', 'People Manager', 'Staffing Consultant',
            'Workforce Planning Lead', 'Human Capital Partner', 'Talent Management Lead',
            'People & Talent Partner', 'TALENT-ACQUISITION',
        ]
        for headline in hiring_profiles:
            with self.subTest(headline=headline):
                self.assertTrue(profile_match(headline, self.spec)[0])
        self.assertTrue(profile_match('Looking for a new opportunity', self.spec)[0])
        self.assertTrue(profile_match('Open to Opportunities', self.spec)[0])
        self.assertTrue(profile_match('People person and community volunteer', self.spec)[0])

    def test_candidate_profile_with_generic_open_to_opportunities_matches_loose_headline_rule(self):
        headline = 'MSc Business Management | Operations & Leadership | Shift Manager | Sales And Marketing | Market Research | Open to Opportunities'
        matched, terms, reason = profile_match(headline, self.spec)
        self.assertTrue(matched)
        self.assertIn('manager', terms)
        self.assertIn('opportunity', terms)

    def test_related_hiring_terms_are_matched_across_punctuation_and_case(self):
        examples = [
            'Talent Acquisition | EMEA', 'Talent & Acquisition Partner',
            'Talent/Acquisition Specialist', 'IT RECRUITING LEAD',
            'Human Resources Business Partner', 'Human Resource Manager',
            'HR | People & Culture', 'People and Talent Partner',
            'Recruitment • Talent Acquisition', 'Talent Sourcing Manager',
        ]
        for text in examples:
            with self.subTest(text=text):
                self.assertTrue(profile_match(text, self.spec)[0])

    def test_headline_extraction_skips_pronouns_location_and_actions(self):
        headline = _select_profile_headline(
            ['She/Her', 'Edinburgh, Scotland, United Kingdom', 'Recruitment, Talent Acquisition Partner'],
            'Avery Smith',
        )
        self.assertEqual(headline, 'Recruitment, Talent Acquisition Partner')

    def test_people_search_returns_only_profiles_matching_selected_mode(self):
        profiles = {
            'https://www.linkedin.com/in/recruiter/': {
                'name': 'Rita Recruiter', 'headline': 'She/Her',
                'headlineCandidates': ['She/Her', 'Recruitment, Talent Acquisition Partner'],
                'preview': 'Rita Recruiter\nRecruitment, Talent Acquisition Partner',
                'profileText': 'Rita Recruiter',
            },
            'https://www.linkedin.com/in/engineer/': {
                'name': 'Evan Engineer', 'headline': 'Playwright Automation Engineer',
                'preview': 'Evan Engineer\nPlaywright Automation Engineer',
                'profileText': 'Evan Engineer Playwright Automation Engineer',
            },
            'https://www.linkedin.com/in/about-only/': {
                'name': 'Avery Operations', 'headline': 'Operations Lead',
                'preview': 'Avery Operations\nOperations Lead',
                'profileText': 'Talent Acquisition Manager',
            },
        }

        class Element:
            def is_displayed(self): return True
            def is_enabled(self): return True

        class Driver:
            live_people_counts = []
            current_url = ''
            def get(self, url): self.current_url = url
            def find_elements(self, by, selector):
                if 'a[href' in selector and '/search/results/people/' in self.current_url:
                    return [Element()]
                if 'p' in selector and self.current_url in profiles:
                    return [Element()]
                return []
            def execute_script(self, script):
                if '/search/results/people/' in self.current_url:
                    return [{'profileUrl': url, 'label': info['name'], 'preview': info['preview']}
                            for url, info in profiles.items()]
                self.live_people_counts.append(len(assistant.state()['people']))
                return profiles[self.current_url]

        class Wait:
            def __init__(self, driver, timeout): self.driver = driver
            def until(self, callback):
                result = callback(self.driver)
                if not result: raise AssertionError('wait condition was false')
                return result

        assistant = NetworkingAssistant()
        with patch('linkedin_networking.WebDriverWait', Wait), patch('linkedin_networking.time.sleep'):
            hiring = assistant._find_people(Driver(), self.spec)
            referrals = assistant._find_people(Driver(), replace(self.spec, search_mode='referral_contacts'))
        self.assertEqual([person['name'] for person in hiring], ['Rita Recruiter'])
        self.assertEqual([person['name'] for person in referrals], ['Evan Engineer'])
        self.assertIn('recruiting', hiring[0]['note'].lower())
        self.assertIn('Recruitment, Talent Acquisition', hiring[0]['headline'])
        self.assertIn('Playwright', referrals[0]['note'])
        self.assertIn(1, Driver.live_people_counts)

    def test_resume_match_ranks_relevant_job_higher(self):
        resume = 'I build Playwright and TypeScript automation for web applications and APIs.'
        relevant = {'title': 'Playwright Automation Engineer', 'location': 'Remote, Dubai', 'description': 'TypeScript Playwright API testing'}
        partial = {'title': 'Playwright with Typescript / Javascript', 'location': 'Dubai', 'description': 'Test automation'}
        unrelated = {'title': 'Accountant', 'location': 'London', 'description': 'Bookkeeping'}
        self.assertGreater(score_job(relevant, self.spec, resume)[0], score_job(unrelated, self.spec, resume)[0])
        self.assertGreater(score_job(partial, self.spec, resume)[0], score_job(unrelated, self.spec, resume)[0])
        self.assertTrue(location_matches('Dubai, UAE (Remote)', self.spec))
        self.assertFalse(location_matches('Chennai, Tamil Nadu, India', self.spec))
        self.assertFalse(location_matches('Dubai, UAE (On-site)', self.spec))

    def test_note_is_personalized_and_within_limit(self):
        note = draft_note('Aisha Khan', 'Playwright testing', 'SDET', 'Delta Electronics')
        self.assertIn('Hi Aisha', note)
        self.assertIn('Playwright testing', note)
        self.assertIn('Delta Electronics', note)
        self.assertLessEqual(len(note), 200)
        self.assertLessEqual(len(draft_note('A very long name', 'x' * 90, 'y' * 90, 'z' * 90)), 200)

    def test_profile_action_text_is_not_used_as_person_name(self):
        self.assertEqual(person_name('View'), '')
        self.assertEqual(person_name("View Muneer Al Wafaa's profile"), 'Muneer Al Wafaa')
        note = draft_note('View', 'Automation', 'Playwright Automation')
        self.assertTrue(note.startswith('Hello,'))
        self.assertNotIn('Hi View', note)
        self.assertNotIn('in your team', note)
        self.assertEqual(post_topic('We are hiring a Playwright Automation Engineer',
                                    ['Playwright Automation Engineer'], ['Playwright']),
                         'the Playwright Automation Engineer opening')

    def test_blank_dashboard_passwords_keep_saved_credentials(self):
        saved = {'email': 'saved@example.com', 'password': 'saved-secret',
                 'gmail': {'senderEmail': 'sender@example.com', 'senderPassword': 'gmail-secret'}}
        incoming = {'email': '', 'password': '', 'gmail': {'senderEmail': '', 'senderPassword': ''}}
        self.assertEqual(merge_linkedin_credentials(incoming, saved), saved | {'profile': ''})

    def test_loaded_campaign_does_not_expose_saved_passwords(self):
        client = app.test_client()
        response = client.get('/api/load-config')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('linkedin', response.get_json()['config'])

    def test_loaded_html_templates_are_editable_text(self):
        import json
        from unittest.mock import mock_open
        saved = {'job': {'emailTemplate': '<p>Hello</p>', 'roles': [
            {'emailTemplate': '<p>Dear team,</p><p>[FULL_NAME]</p>'},
            {'emailTemplate': 'Plain message'}]}}
        with patch('professional_dashboard_api.os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(saved))):
            response = app.test_client().get('/api/load-config')
        self.assertEqual(response.status_code, 200)
        job = response.get_json()['config']['job']
        self.assertEqual(job['emailTemplate'], 'Hello')
        self.assertEqual(job['roles'][0]['emailTemplate'], 'Dear team,\n\n[FULL_NAME]')
        self.assertEqual(job['roles'][1]['emailTemplate'], 'Plain message')

    def test_only_linkedin_profile_urls_can_be_sent(self):
        self.assertEqual(profile_url('https://www.linkedin.com/in/aisha/?tracking=1'), 'https://www.linkedin.com/in/aisha/')
        self.assertEqual(profile_url('https://linkedin.com/IN/Aisha/?tracking=1'), 'https://www.linkedin.com/in/aisha/')
        self.assertIsNone(profile_url('https://evil.example/in/aisha'))
        with self.assertRaises(ValueError):
            send_connection_note(None, {'profileUrl': 'https://evil.example/in/aisha'}, 'Hello')

    def test_reviewed_note_requires_ready_browser_and_queues_with_feedback(self):
        assistant = NetworkingAssistant()
        person = {'id': 'candidate-1', 'profileUrl': 'https://www.linkedin.com/in/aisha/', 'status': 'draft'}
        assistant._state.update(status='idle', people=[person])
        with self.assertRaisesRegex(ValueError, 'Finish the search'):
            assistant.send(person['id'], 'Hi Aisha')

        assistant._state.update(status='ready', people=[person])
        state = assistant.send(person['id'], 'Hi Aisha')
        self.assertEqual(state['people'][0]['status'], 'queued')
        self.assertEqual(state['people'][0]['note'], 'Hi Aisha')
        self.assertEqual(assistant._queue.get_nowait(), (person['id'], 'Hi Aisha'))

    def test_batch_notes_are_queued_in_candidate_order(self):
        assistant = NetworkingAssistant()
        people = [
            {'id': 'one', 'profileUrl': 'https://www.linkedin.com/in/one/', 'status': 'draft', 'note': 'Draft one'},
            {'id': 'two', 'profileUrl': 'https://www.linkedin.com/in/two/', 'status': 'error', 'note': 'Draft two'},
        ]
        assistant._state.update(status='ready', people=people)
        state = assistant.send_all({'one': 'Reviewed one'})
        self.assertEqual([p['status'] for p in state['people']], ['queued', 'queued'])
        self.assertEqual(assistant._queue.get_nowait(), ('one', 'Reviewed one'))
        self.assertEqual(assistant._queue.get_nowait(), ('two', 'Draft two'))

    def test_batch_skips_same_profile_even_with_url_case_and_tracking_variants(self):
        assistant = NetworkingAssistant()
        people = [
            {'id': 'one', 'profileUrl': 'https://www.linkedin.com/in/Aisha/', 'status': 'draft', 'note': 'First'},
            {'id': 'two', 'profileUrl': 'https://linkedin.com/in/aisha/?trk=people', 'status': 'draft', 'note': 'Second'},
        ]
        assistant._state.update(status='ready', people=people)
        with patch.object(assistant, '_invite_history', return_value={}):
            state = assistant.send_all({})
        self.assertEqual([p['status'] for p in state['people']], ['queued', 'duplicate'])
        self.assertEqual(assistant._queue.get_nowait(), ('one', 'First'))
        self.assertTrue(assistant._queue.empty())

    def test_sent_history_canonicalizes_and_suppresses_profile_variants(self):
        assistant = NetworkingAssistant()
        person = {'name': 'Aisha Khan', 'profileUrl': 'https://www.linkedin.com/in/Aisha/?tracking=1'}
        with tempfile.TemporaryDirectory() as folder, patch('linkedin_networking.SENT_FILE', Path(folder) / 'invites.json'):
            assistant._record_attempt(person, 'Hi Aisha')
            self.assertIn(_profile_key('https://linkedin.com/in/aisha?trk=abc'), assistant._sent_profiles())
            self.assertEqual(assistant._invite_history()[_profile_key(person['profileUrl'])]['status'], 'attempting')
            assistant._record_sent(person, 'Hi Aisha')
            self.assertEqual(assistant._invite_history()[_profile_key(person['profileUrl'])]['status'], 'sent')

    def test_search_and_sender_use_separate_browsers_and_sender_reuses_its_driver(self):
        events = []

        class Driver:
            def __init__(self, name): self.name = name
            def quit(self): events.append(f'quit:{self.name}')

        class BrowserOptions:
            def add_argument(self, argument): pass

        search_driver, sender_driver = Driver('search'), Driver('sender')
        people = [{
            'id': 'candidate-1', 'name': 'Aisha Khan',
            'profileUrl': 'https://www.linkedin.com/in/aisha/',
            'headline': 'Talent Acquisition Partner', 'note': 'Draft note', 'status': 'draft',
        }]
        assistant = NetworkingAssistant()
        assistant._last_profile_scan = {'discovered': 1, 'checked': 1, 'qualified': 1}

        def sign_in(driver, credentials): events.append(f'login:{driver.name}')
        def send_note(driver, candidate, note): events.append(f'send:{driver.name}:{candidate["profileUrl"]}:{note}')

        with patch('linkedin_networking.Options', return_value=BrowserOptions()), \
             patch('linkedin_networking.webdriver.Chrome', side_effect=[search_driver, sender_driver]) as chrome, \
             patch('linkedin_networking.sign_in', side_effect=sign_in), \
             patch('linkedin_networking.read_resume_text', return_value='resume text'), \
             patch.object(assistant, '_find_jobs', return_value=[]), \
             patch.object(assistant, '_find_people', return_value=people), \
             patch.object(assistant, '_invite_history', return_value={}), \
             patch.object(assistant, '_record_attempt'), \
             patch.object(assistant, '_record_sent'), \
             patch('linkedin_networking.send_connection_note', side_effect=send_note):
            worker = threading.Thread(target=assistant._run, args=(self.spec, {'email': 'test', 'password': 'test'}))
            worker.start()
            for _ in range(100):
                if assistant.state()['status'] == 'ready': break
                time.sleep(0.01)
            self.assertEqual(assistant.state()['status'], 'ready')
            self.assertEqual(chrome.call_count, 1, 'sender browser must wait for the batch action')
            self.assertEqual(assistant.send_all({'candidate-1': 'Reviewed note'})['people'][0]['status'], 'queued')
            for _ in range(100):
                if assistant.state()['people'][0]['status'] == 'sent': break
                time.sleep(0.01)
            assistant._stop.set()
            assistant._queue.put(None)
            worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertEqual(chrome.call_count, 2)
        self.assertLess(events.index('quit:search'), events.index('send:sender:https://www.linkedin.com/in/aisha/:Reviewed note'))
        self.assertIn('login:sender', events)

    def test_lost_sender_session_marks_current_uncertain_and_stops_batch(self):
        class Driver:
            def __init__(self, name): self.name = name
            def quit(self): pass

        class BrowserOptions:
            def add_argument(self, argument): pass

        search_driver, sender_driver = Driver('search'), Driver('sender')
        people = [
            {'id': 'one', 'name': 'First Person', 'profileUrl': 'https://www.linkedin.com/in/first/', 'note': 'Hi', 'status': 'draft'},
            {'id': 'two', 'name': 'Second Person', 'profileUrl': 'https://www.linkedin.com/in/second/', 'note': 'Hi', 'status': 'draft'},
        ]
        assistant = NetworkingAssistant()
        assistant._last_profile_scan = {'discovered': 2, 'checked': 2, 'qualified': 2}

        def send_note(driver, person, note):
            raise InvalidSessionIdException('invalid session id')

        with patch('linkedin_networking.Options', return_value=BrowserOptions()), \
             patch('linkedin_networking.webdriver.Chrome', side_effect=[search_driver, sender_driver]), \
             patch('linkedin_networking.sign_in'), \
             patch('linkedin_networking.read_resume_text', return_value='resume text'), \
             patch.object(assistant, '_find_jobs', return_value=[]), \
             patch.object(assistant, '_find_people', return_value=people), \
             patch.object(assistant, '_invite_history', return_value={}), \
             patch.object(assistant, '_sent_profiles', return_value=set()), \
             patch.object(assistant, '_record_attempt'), \
             patch.object(assistant, '_record_uncertain'), \
             patch.object(assistant, '_clear_attempt'), \
             patch('linkedin_networking.send_connection_note', side_effect=send_note):
            worker = threading.Thread(target=assistant._run, args=(self.spec, {'email': 'test', 'password': 'test'}))
            worker.start()
            for _ in range(100):
                if assistant.state()['status'] == 'ready': break
                time.sleep(0.01)
            assistant.send_all({'one': 'First note', 'two': 'Second note'})
            for _ in range(100):
                statuses = [person['status'] for person in assistant.state()['people']]
                if statuses == ['uncertain', 'error']: break
                time.sleep(0.01)
            state = assistant.state()
            assistant._stop.set()
            assistant._queue.put(None)
            worker.join(timeout=2)

        self.assertEqual([person['status'] for person in state['people']], ['uncertain', 'error'])
        self.assertIn('Delivery is uncertain', state['people'][0]['error'])
        self.assertIn('was not attempted', state['people'][1]['error'])
        self.assertFalse(worker.is_alive())

    def test_removed_ai_route_and_network_input_validation(self):
        client = app.test_client()
        self.assertEqual(client.post('/api/start-aibot', json={}).status_code, 404)
        with patch('professional_dashboard_api.networking_assistant.start', side_effect=ValueError('Invalid search settings')):
            response = client.post('/api/network/search', json={'titles': ['SDET'], 'locations': ['Dubai'], 'resumePath': ''})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(client.post('/api/network/send-note', json={'candidateId': 'missing', 'note': 'Hi'}).status_code, 400)
        self.assertEqual(client.post('/api/network/send-batch', json={'notes': {}}).status_code, 400)
        self.assertIn(b'Job Search + Networking Assistant', client.get('/dashboard').data)

    def test_reviewed_note_uses_connect_add_note_and_note_specific_send(self):
        events = []

        class Element:
            value = ''
            visible = True

            def __init__(self, name):
                self.name = name

            @property
            def text(self):
                return 'Send' if self.name == 'send' else 'Send without a note' if self.name == 'send_without_note' else self.name

            def is_displayed(self):
                return self.visible

            def is_enabled(self):
                return True

            def click(self):
                events.append(self.name)
                if self.name == 'follow':
                    raise StaleElementReferenceException('profile header refreshed')
                if self.name == 'more':
                    raise StaleElementReferenceException('profile menu refreshed')
                if self.name == 'connect':
                    modal.visible = True
                    add_note.visible = True
                    raise StaleElementReferenceException('connect opened the dialog')
                if self.name == 'add_note':
                    textarea.visible = True
                    raise StaleElementReferenceException('note dialog refreshed')
                if self.name == 'send':
                    textarea.visible = False
                    modal.visible = False
                    raise StaleElementReferenceException('send closed the dialog')

            def find_elements(self, by, selector):
                if self.name == 'dialog':
                    return [add_note] if 'Add a note' in selector else [send]
                if self.name == 'main':
                    if 'Follow' in selector:
                        return [follow]
                    if 'More' in selector:
                        return [more]
                    if 'Connect' in selector:
                        return [connect]
                return []

            def clear(self):
                self.value = ''

            def send_keys(self, value):
                self.value += value
                events.append('typed')

            def get_attribute(self, name):
                if name == 'aria-label':
                    return None if self.name == 'send' else 'Send without a note' if self.name == 'send_without_note' else None
                return self.value if name == 'value' else None

        follow, more, connect = Element('follow'), Element('more'), Element('connect')
        add_note, send = Element('add_note'), Element('send')
        send_without_note = Element('send_without_note')
        add_note.visible = False
        modal = Element('modal')
        modal.visible = False
        textarea = Element('textarea')
        textarea.visible = False
        main = Element('main')

        class Driver:
            def get(self, url):
                events.append('profile')

            def find_elements(self, by, selector):
                if selector in {'main', '//main'}:
                    return [main]
                if 'Add a note' in selector:
                    return [add_note]
                if 'Send invitation' in selector or "normalize-space(.)='Send'" in selector:
                    return [send, send_without_note]
                if 'textarea' in selector or '#custom-message' in selector:
                    return [textarea]
                if '.artdeco-modal' in selector:
                    return [modal]
                if 'Follow' in selector:
                    return [follow]
                if 'More' in selector:
                    return [more]
                if 'Connect' in selector:
                    return [connect]
                return []

        class Wait:
            def __init__(self, driver, timeout):
                self.driver = driver

            def until(self, callback):
                result = callback(self.driver)
                if not result:
                    raise AssertionError('wait condition was false')
                return result

        def scoped_click_side_effect(driver, get_control, action, transitioned, timeout=20):
            events.append('connect')
            modal.visible = True
            add_note.visible = True

        with patch('linkedin_networking.WebDriverWait', Wait), \
             patch('linkedin_networking._profile_heading_text', return_value=''), \
             patch('linkedin_networking._profile_connect_control', return_value=connect), \
             patch('linkedin_networking._profile_more_control', return_value=None), \
             patch('linkedin_networking._click_scoped_control', side_effect=scoped_click_side_effect):
            self.assertTrue(send_connection_note(Driver(), {'profileUrl': 'https://www.linkedin.com/in/aisha/'}, 'Hi Aisha'))
        self.assertEqual(events, ['profile', 'connect', 'add_note', 'typed', 'send'])

    def test_profile_without_connect_shows_actionable_failure(self):
        class Element:
            def is_displayed(self):
                return True

            def is_enabled(self):
                return True

            def find_elements(self, by, selector):
                return []

        class Driver:
            def get(self, url):
                pass

            def find_elements(self, by, selector):
                return [main] if selector == '//main' else []

        main = Element()
        with patch('linkedin_networking._wait_visible', return_value=main), \
             patch('linkedin_networking._profile_heading_text', return_value=''), \
             patch('linkedin_networking._profile_connect_control', return_value=None), \
             patch('linkedin_networking._profile_more_control', return_value=None), \
             patch('linkedin_networking._menu_message_control', return_value=None), \
             patch('linkedin_networking._profile_message_control', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'no usable Connect or Message action.*no outreach was sent'):
                send_connection_note(Driver(), {'profileUrl': 'https://www.linkedin.com/in/already-connected/'}, 'Hi')

    def test_message_is_used_when_connect_is_unavailable(self):
        main = object()
        message_control = object()
        candidate = {'name': 'Member Name', 'profileUrl': 'https://www.linkedin.com/in/member-name/'}
        class Driver:
            def get(self, url): pass
            def find_elements(self, by, selector): return [main] if selector == '//main' else []

        driver = Driver()
        sent = []

        def send_message(current_driver, current_candidate, note, control):
            sent.append((current_candidate, note, control()))
            current_candidate['deliveryMethod'] = 'direct_message'
            return True

        with patch('linkedin_networking._wait_visible', return_value=main), \
             patch('linkedin_networking._profile_heading_text', return_value='Member Name'), \
             patch('linkedin_networking._profile_connect_control', return_value=None), \
             patch('linkedin_networking._profile_more_control', return_value=None), \
             patch('linkedin_networking._profile_message_control', return_value=message_control), \
             patch('linkedin_networking._menu_message_control', return_value=None), \
             patch('linkedin_networking._send_direct_message', side_effect=send_message):
            self.assertTrue(send_connection_note(driver, candidate, 'Reviewed note'))

        self.assertEqual(sent, [(candidate, 'Reviewed note', message_control)])
        self.assertEqual(candidate['deliveryMethod'], 'direct_message')

    def test_message_only_profile_sends_to_verified_compose_recipient(self):
        class Element:
            def __init__(self, name, value='', href=''):
                self.name = name
                self.value = value
                self.href = href
                self.visible = True

            @property
            def text(self):
                return self.value

            def is_displayed(self): return self.visible
            def is_enabled(self): return True
            def click(self): pass
            def get_attribute(self, name):
                return self.href if name == 'href' else self.value if name in {'innerText', 'textContent'} else None
            def send_keys(self, *keys):
                from selenium.webdriver.common.keys import Keys
                for key in keys:
                    if key == Keys.BACKSPACE:
                        self.value = ''
                    elif key in {Keys.CONTROL, 'a'}:
                        continue
                    else:
                        self.value += key

        editor = Element('editor')
        recipient = Element('recipient', 'Monika Sai Degapudi Mohan Reddy', '/in/monika-sai112/')
        send = Element('send')
        state = {'open': False}

        class Driver:
            current_url = 'https://www.linkedin.com/in/monika-sai112/'
            def find_elements(self, by, selector):
                if 'msg-form__contenteditable' in selector or "aria-label*='Write a message'" in selector:
                    return [editor] if state['open'] else []
                if 'msg-compose__profile-link' in selector:
                    return [recipient] if state['open'] else []
                if 'msg-form__send-btn' in selector:
                    return [send] if state['open'] else []
                return []

        def click_action(driver, by, selector, action, timeout=8, transitioned=None):
            if action == 'Open Message':
                state['open'] = True
            elif action == 'Send reviewed LinkedIn message':
                editor.value = ''

        class Wait:
            def __init__(self, driver, timeout): pass
            def until(self, callback):
                result = callback(Driver())
                if not result: raise AssertionError('wait condition was false')
                return result

        candidate = {'name': 'Monika Sai Degapudi Mohan Reddy', 'profileUrl': 'https://www.linkedin.com/in/monika-sai112/'}
        with patch('linkedin_networking.WebDriverWait', Wait), patch('linkedin_networking._click_action', side_effect=click_action):
            self.assertTrue(_send_direct_message(Driver(), candidate, 'Hi Monika, I am exploring QA roles.', '//a[.="Message"]'))
        self.assertEqual(candidate['deliveryMethod'], 'direct_message')
        self.assertEqual(editor.value, '')

    def test_message_premium_upsell_is_reported_without_subscribing_or_sending(self):
        events = []
        state = {'premium': False}

        class Modal:
            text = 'Try Premium free for 1 month to message this member'
            def is_displayed(self): return True

        class Driver:
            current_url = 'https://www.linkedin.com/in/member/'
            def find_elements(self, by, selector):
                return [Modal()] if state['premium'] and "role='dialog'" in selector else []

        def click_action(driver, by, selector, action, timeout=8, transitioned=None):
            events.append(action)
            state['premium'] = True

        class Wait:
            def __init__(self, driver, timeout): pass
            def until(self, callback):
                result = callback(Driver())
                if not result: raise AssertionError('wait condition was false')
                return result

        with patch('linkedin_networking.WebDriverWait', Wait), patch('linkedin_networking._click_action', side_effect=click_action):
            with self.assertRaisesRegex(RuntimeError, 'requires Premium.*No message was sent'):
                _send_direct_message(
                    Driver(), {'name': 'Member', 'profileUrl': 'https://www.linkedin.com/in/member/'},
                    'Hello, I am exploring roles.', '//a[.="Message"]'
                )
        self.assertEqual(events, ['Open Message'])


if __name__ == '__main__':
    unittest.main()
