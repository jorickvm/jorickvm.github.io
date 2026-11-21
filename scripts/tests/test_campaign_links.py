import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_site


class CampaignLinkTests(unittest.TestCase):
    def test_each_part_of_the_site_has_its_campaign(self):
        cases = {
            'learn/spain-183-day-tax-residency.html': 'web-article',
            'learn/index.html': 'web-article',
            'learn/schengen-calculator.html': 'web-calc',
            'help/index.html': 'web-help',
            'help/add-a-trip.html': 'web-help',
            'about.html': 'web-other',
            '404.html': 'web-other',
        }
        for path, campaign in cases.items():
            with self.subTest(path=path):
                self.assertEqual(build_site.campaign_for(path, {}), campaign)

    def test_every_calculator_page_is_a_calculator(self):
        for path in build_site.CALCULATOR_PAGES:
            with self.subTest(path=path):
                self.assertEqual(build_site.campaign_for(path, {}), 'web-calc')

    def test_a_record_can_set_its_own_campaign(self):
        self.assertEqual(build_site.campaign_for('press/index.html', {'campaign': 'press'}), 'press')
        self.assertEqual(build_site.campaign_for('learn/calculators.html', {'campaign': 'web-calc'}), 'web-calc')

    def test_registered_pages_carry_the_campaigns_the_site_reports(self):
        pages = json.loads(build_site.PAGE_DATA_PATH.read_text(encoding='utf-8'))['pages']
        campaigns = {page['path']: build_site.campaign_for(page['path'], page) for page in pages}
        self.assertEqual(campaigns['index.html'], 'web-home')
        self.assertEqual(campaigns['visa-limits.html'], 'web-home')
        self.assertEqual(campaigns['app/import/index.html'], 'web-calc')
        self.assertEqual(campaigns['press/index.html'], 'press')
        self.assertEqual(campaigns['privacy.html'], 'web-other')

    def test_links_carry_the_campaign_and_the_product_page(self):
        plain = f'<a href="{build_site.APP_STORE_URL}">Get</a>'
        tagged = build_site.with_campaign_links(plain, 'web-help')
        self.assertIn('ct=web-help&amp;mt=8"', tagged)
        self.assertNotIn(build_site.APP_STORE_URL, tagged)
        with_page = build_site.with_campaign_links(plain, 'web-calc', 'abc')
        self.assertIn('ct=web-calc&amp;mt=8&amp;ppid=abc"', with_page)

    def test_a_named_campaign_fits_the_app_store_limit(self):
        records = json.loads(build_site.PAGE_DATA_PATH.read_text(encoding='utf-8'))['pages']
        records += json.loads(build_site.HUB_DATA_PATH.read_text(encoding='utf-8'))['hubs']
        named = {str(record['campaign']) for record in records if record.get('campaign')}
        self.assertIn('web-home', named)
        for campaign in named:
            with self.subTest(campaign=campaign):
                self.assertLessEqual(len(campaign), 30)
                self.assertRegex(campaign, r'^[a-z0-9-]+$')


if __name__ == '__main__':
    unittest.main()
