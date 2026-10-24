"""Test čištění HTML převedeného z DOCX."""

from politika.dokumenty.prevod import vycisti_html


def test_vycisti_html_odstrani_skripty_a_nebezpecne_odkazy():
    html = ('<p onclick="x()">Text <a href="javascript:alert(1)">zlý</a> '
            '<a href="https://www.psp.cz">dobrý</a></p><script>alert(1)</script>'
            '<img src="http://evil/x.png"><table><tr><td colspan="2">A</td></tr></table>')
    cisty = vycisti_html(html)
    assert "onclick" not in cisty and "javascript" not in cisty and "alert" not in cisty
    assert '<a href="https://www.psp.cz">dobrý</a>' in cisty
    assert "<img" not in cisty
    assert '<td colspan="2">A</td>' in cisty
