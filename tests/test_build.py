"""
Unit tests for slides_builder.build — core parsing and rendering functions.
"""

import re
import textwrap

import pytest

from slides_builder.build import (
    apply_fragments,
    extract_notes,
    extract_slide_directive,
    extract_yaml_front_matter,
    process_md_chunk,
    split_on_hr,
    wrap_section,
)


# ---------------------------------------------------------------------------
# split_on_hr
# ---------------------------------------------------------------------------


class TestSplitOnHr:
    def test_single_chunk_returned_as_is(self):
        assert split_on_hr("## Hello\n\nContent.") == ["## Hello\n\nContent."]

    def test_separator_produces_two_chunks(self):
        result = split_on_hr("## A\n\n---\n\n## B")
        assert len(result) == 2
        assert "## A" in result[0]
        assert "## B" in result[1]

    def test_multiple_separators(self):
        result = split_on_hr("## A\n---\n## B\n---\n## C")
        assert len(result) == 3

    def test_empty_chunks_filtered(self):
        # Two consecutive --- produce an empty chunk between them; it should be dropped.
        result = split_on_hr("## A\n\n---\n\n---\n\n## B")
        assert len(result) == 2

    # Front matter handling (fixed in split_on_hr)

    def test_front_matter_preserved_in_one_chunk(self):
        md = "---\nclass: dark\n---\n## Slide"
        result = split_on_hr(md)
        assert len(result) == 1
        assert result[0].startswith("---")
        assert "class: dark" in result[0]
        assert "## Slide" in result[0]

    def test_front_matter_then_separator(self):
        md = "---\nclass: hero\n---\n# Title\n\n---\n\n## Second"
        result = split_on_hr(md)
        assert len(result) == 2
        assert "class: hero" in result[0]
        assert "# Title" in result[0]
        assert "## Second" in result[1]

    def test_per_chunk_front_matter(self):
        md = "---\nclass: hero\n---\n# A\n\n---\n---\nclass: dark\n---\n## B"
        result = split_on_hr(md)
        assert len(result) == 2
        assert "class: hero" in result[0]
        assert "class: dark" in result[1]

    # Fenced code block protection

    def test_separator_inside_fence_not_split(self):
        md = "## Slide\n```yaml\n---\nkey: val\n---\n```\n\nAfter."
        result = split_on_hr(md)
        assert len(result) == 1

    def test_front_matter_fence_combo(self):
        md = "---\nclass: dark\n---\n## Slide\n```bash\n---\n```"
        result = split_on_hr(md)
        assert len(result) == 1
        assert "class: dark" in result[0]


# ---------------------------------------------------------------------------
# extract_yaml_front_matter
# ---------------------------------------------------------------------------


class TestExtractYamlFrontMatter:
    def test_no_front_matter(self):
        fm, body = extract_yaml_front_matter("## Hello")
        assert fm == {}
        assert body == "## Hello"

    def test_basic_key_value(self):
        fm, body = extract_yaml_front_matter("---\nclass: dark\n---\n## Slide")
        assert fm == {"class": "dark"}
        assert "## Slide" in body
        assert "---" not in body

    def test_quoted_value_stripped(self):
        fm, _ = extract_yaml_front_matter('---\nbackground: "#1e293b"\n---\n## Hi')
        assert fm["background"] == "#1e293b"

    def test_single_quoted_value_stripped(self):
        fm, _ = extract_yaml_front_matter("---\ntitle: 'My Talk'\n---\n## Hi")
        assert fm["title"] == "My Talk"

    def test_multiple_keys(self):
        fm, _ = extract_yaml_front_matter(
            "---\nclass: hero\nincremental: true\n---\n## Hi"
        )
        assert fm["class"] == "hero"
        assert fm["incremental"] == "true"

    def test_unclosed_front_matter_ignored(self):
        # No closing --- means no front matter.
        fm, body = extract_yaml_front_matter("---\nclass: dark\n## Content")
        assert fm == {}

    def test_empty_front_matter(self):
        fm, body = extract_yaml_front_matter("---\n---\n## Slide")
        assert fm == {}
        assert "## Slide" in body


# ---------------------------------------------------------------------------
# extract_slide_directive
# ---------------------------------------------------------------------------


class TestExtractSlideDirective:
    def test_no_directive(self):
        attrs, body = extract_slide_directive("## Hello\n\nContent.")
        assert attrs == {}
        assert body == "## Hello\n\nContent."

    def test_directive_parsed(self):
        chunk = '<!-- .slide: class="hero" -->\n## Title'
        attrs, body = extract_slide_directive(chunk)
        assert attrs == {"class": "hero"}
        assert "<!-- .slide:" not in body
        assert "## Title" in body

    def test_multiple_attrs(self):
        chunk = '<!-- .slide: class="dark" data-background="#1e293b" -->'
        attrs, _ = extract_slide_directive(chunk)
        assert attrs["class"] == "dark"
        assert attrs["data-background"] == "#1e293b"

    def test_directive_inside_fence_ignored(self):
        # Bug fix: directives inside code blocks must not be applied.
        chunk = '## Example\n```html\n<!-- .slide: class="dark" -->\n```'
        attrs, body = extract_slide_directive(chunk)
        assert attrs == {}
        assert "## Example" in body

    def test_directive_outside_fence_applied(self):
        chunk = '<!-- .slide: class="accent" -->\n## Slide\n```\n---\n```'
        attrs, _ = extract_slide_directive(chunk)
        assert attrs["class"] == "accent"


# ---------------------------------------------------------------------------
# extract_notes
# ---------------------------------------------------------------------------


class TestExtractNotes:
    def test_no_notes(self):
        content, notes = extract_notes("## Slide\n\nContent.")
        assert notes == ""
        assert "## Slide" in content

    def test_notes_split(self):
        content, notes = extract_notes("## Slide\n\nNote:\nMy notes.")
        assert "## Slide" in content
        assert "Note:" not in content
        assert notes == "My notes."

    def test_notes_multiline(self):
        _, notes = extract_notes("## Slide\n\nNote:\nLine one.\nLine two.")
        assert "Line one." in notes
        assert "Line two." in notes


# ---------------------------------------------------------------------------
# apply_fragments
# ---------------------------------------------------------------------------


class TestApplyFragments:
    def test_adds_fragment_class_to_li(self):
        html = "<ul><li>one</li><li>two</li></ul>"
        result = apply_fragments(html)
        assert result == '<ul><li class="fragment">one</li><li class="fragment">two</li></ul>'

    def test_no_li_unchanged(self):
        html = "<p>Just a paragraph.</p>"
        assert apply_fragments(html) == html

    def test_nested_lists_both_get_fragment(self):
        html = "<ul><li>outer<ul><li>inner</li></ul></li></ul>"
        result = apply_fragments(html)
        assert result.count('class="fragment"') == 2

    def test_ordered_list_items(self):
        html = "<ol><li>first</li><li>second</li></ol>"
        result = apply_fragments(html)
        assert result.count('class="fragment"') == 2


# ---------------------------------------------------------------------------
# process_md_chunk — integration
# ---------------------------------------------------------------------------


class TestProcessMdChunk:
    def _section_tag(self, html: str) -> str:
        m = re.search(r"<section[^>]*>", html)
        assert m, f"No <section> tag found in: {html!r}"
        return m.group(0)

    def test_plain_chunk(self):
        html = process_md_chunk("## Hello\n\nWorld.")
        assert "<section>" in html
        assert "<h2>Hello</h2>" in html

    # incremental

    def test_incremental_true_adds_fragments(self):
        chunk = "---\nincremental: true\n---\n## Slide\n\n- alpha\n- beta"
        html = process_md_chunk(chunk)
        assert html.count('class="fragment"') == 2

    def test_incremental_false_no_fragments(self):
        chunk = "---\nincremental: false\n---\n## Slide\n\n- alpha\n- beta"
        html = process_md_chunk(chunk)
        assert 'class="fragment"' not in html

    def test_incremental_not_in_section_attrs(self):
        chunk = "---\nincremental: true\n---\n## Slide\n\n- item"
        html = process_md_chunk(chunk)
        assert 'incremental' not in self._section_tag(html)

    def test_incremental_via_slide_directive(self):
        chunk = '<!-- .slide: incremental="true" -->\n## Slide\n\n- one\n- two'
        html = process_md_chunk(chunk)
        assert html.count('class="fragment"') == 2

    def test_incremental_truthy_variants(self):
        for val in ("true", "yes", "1", "on"):
            chunk = f"---\nincremental: {val}\n---\n## S\n\n- x"
            html = process_md_chunk(chunk)
            assert 'class="fragment"' in html, f"Expected fragments for incremental: {val}"

    # Themes via front matter

    def test_hero_class_in_section(self):
        html = process_md_chunk("---\nclass: hero\n---\n# Title")
        assert 'class="hero"' in self._section_tag(html)

    def test_dark_class_and_background(self):
        html = process_md_chunk('---\nclass: dark\nbackground: "#1e293b"\n---\n## Slide')
        tag = self._section_tag(html)
        assert 'class="dark"' in tag
        assert 'data-background="#1e293b"' in tag

    def test_statement_class(self):
        html = process_md_chunk("---\nclass: statement\n---\n> Key point.")
        assert 'class="statement"' in self._section_tag(html)

    # Background shortcut expansion

    def test_background_image_prefixed(self):
        html = process_md_chunk('---\nbackground-image: "url(img.png)"\n---\n## Slide')
        assert 'data-background-image="url(img.png)"' in self._section_tag(html)

    # Speaker notes

    def test_speaker_notes_rendered(self):
        html = process_md_chunk("## Slide\n\nNote:\nMy notes here.")
        assert '<aside class="notes">' in html
        assert "My notes here." in html

    # Directive overrides front matter

    def test_directive_overrides_front_matter(self):
        chunk = '---\nclass: dark\n---\n<!-- .slide: class="hero" -->\n## Slide'
        html = process_md_chunk(chunk)
        # slide directive wins over front matter
        assert 'class="hero"' in self._section_tag(html)
