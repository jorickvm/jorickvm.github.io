import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_site

IMAGES = {
    "assets/home/v2/shot.webp": {"width": 1320, "variants": {"480": {}, "720": {}}},
    "assets/home/v2/shot-light.webp": {"width": 1320, "variants": {"480": {}, "720": {}}},
    "assets/home/iphone-frame-blue.webp": {"width": 980, "variants": {"480": {}, "720": {}}},
}

HERO = """<div class="hx-device">
  <div class="hx-screen">
    <img class="shot-dark" src="/assets/home/v2/shot.webp?v=1a" alt="Dark" width="1320" height="2868" fetchpriority="high" />
    <img class="shot-light" src="/assets/home/v2/shot-light.webp?v=1a" alt="Light" width="1320" height="2868" />
  </div>
  <img class="hx-frame" src="/assets/home/iphone-frame-blue.webp?v=2b" alt="" width="980" height="2000" />
</div>"""


class ResponsiveImageTests(unittest.TestCase):
    def render(self, markup):
        with patch.object(build_site, "load_responsive_images", return_value=IMAGES):
            return build_site.render_responsive_images(markup)

    def tags(self, markup):
        return build_site.IMG_TAG.findall(self.render(markup))

    def test_screenshot_offers_resized_copies_and_keeps_the_full_size_source(self):
        dark = self.tags(HERO)[0]
        self.assertIn('src="/assets/home/v2/shot.webp?v=1a"', dark)
        self.assertIn(
            'srcset="/assets/home/web/480/v2/shot.webp?v=1a 480w, '
            '/assets/home/web/720/v2/shot.webp?v=1a 720w, /assets/home/v2/shot.webp?v=1a 1320w"',
            dark,
        )
        self.assertIn(f'sizes="{build_site.PHONE_SCREEN_SIZES}"', dark)

    def test_relative_sources_keep_their_prefix(self):
        tag = self.tags('<div class="hx-screen"><img class="shot-dark" src="../assets/home/v2/shot.webp" /></div>')[0]
        self.assertIn("../assets/home/web/480/v2/shot.webp 480w", tag)

    def test_only_the_light_screenshot_is_deferred(self):
        dark, light, _ = self.tags(HERO)
        self.assertNotIn("loading=", dark)
        self.assertIn('loading="lazy"', light)

    def test_a_frame_that_loads_with_the_page_is_prioritised(self):
        self.assertIn('fetchpriority="high"', self.tags(HERO)[2])
        lazy = self.tags(HERO.replace('height="2000" />', 'height="2000" loading="lazy" />'))[2]
        self.assertNotIn("fetchpriority", lazy)
        self.assertIn(f'sizes="{build_site.PHONE_FRAME_SIZES}"', lazy)

    def test_case_cards_use_their_own_width(self):
        tag = self.tags('<span class="hx-case-shot"><img class="shot-dark" src="assets/home/v2/shot.webp" /></span>')[0]
        self.assertIn(f'sizes="{build_site.CASE_SHOT_SIZES}"', tag)

    def test_other_images_are_left_alone(self):
        for markup in (
            '<div class="hx-screen"><img class="shot-dark" src="/assets/home/v2/unknown.webp" /></div>',
            '<p><img class="shot-dark" src="/assets/home/v2/shot.webp" /></p>',
            '<img class="rule-flag" src="/assets/flags/web/fr.webp" alt="" />',
        ):
            self.assertEqual(self.render(markup), markup)

    def test_every_listed_copy_is_a_file(self):
        root = Path(__file__).resolve().parents[2]
        for source, record in build_site.load_responsive_images().items():
            for width in record["variants"]:
                self.assertTrue((root / build_site.variant_path(source, int(width))).is_file(), (source, width))


if __name__ == "__main__":
    unittest.main()
