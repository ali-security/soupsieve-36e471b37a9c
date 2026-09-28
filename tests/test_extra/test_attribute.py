"""Test attribute selectors."""
from .. import util
import os
import subprocess
import sys
import soupsieve as sv

# Compile a selector read from `stdin` and report whether it failed with a syntax error.
COMPILE_SCRIPT = """
import sys
import soupsieve as sv
try:
    sv.compile(sys.stdin.read())
except sv.SelectorSyntaxError:
    sys.exit(0)
sys.exit(1)
"""

# Generous upper bound for a single compile in a fresh interpreter. A well-behaved pattern fails
# in milliseconds, while catastrophic backtracking on the payloads below never finishes.
COMPILE_TIMEOUT = 30


class TestAttribute(util.TestCase):
    """Test attribute selectors."""

    MARKUP = """
    <div id="div">
    <p id="0">Some text <span id="1"> in a paragraph</span>.</p>
    <a id="2" href="http://google.com">Link</a>
    <span id="3">Direct child</span>
    <pre id="pre">
    <span id="4">Child 1</span>
    <span id="5">Child 2</span>
    <span id="6">Child 3</span>
    </pre>
    </div>
    """

    def test_attribute_not_equal_no_quotes(self):
        """Test attribute with value that does not equal specified value (no quotes)."""

        # No quotes
        self.assert_selector(
            self.MARKUP,
            'body [id!=\\35]',
            ["div", "0", "1", "2", "3", "pre", "4", "6"],
            flags=util.HTML5
        )

    def test_attribute_not_equal_quotes(self):
        """Test attribute with value that does not equal specified value (quotes)."""

        # Quotes
        self.assert_selector(
            self.MARKUP,
            "body [id!='5']",
            ["div", "0", "1", "2", "3", "pre", "4", "6"],
            flags=util.HTML5
        )

    def test_attribute_not_equal_double_quotes(self):
        """Test attribute with value that does not equal specified value (double quotes)."""

        # Double quotes
        self.assert_selector(
            self.MARKUP,
            'body [id!="5"]',
            ["div", "0", "1", "2", "3", "pre", "4", "6"],
            flags=util.HTML5
        )

    def assert_syntax_error_no_timeout(self, pattern):
        """
        Assert that compiling the pattern fails with a syntax error and does not hang.

        The pattern is first compiled in a separate interpreter that is killed if it does not finish
        in time, so catastrophic backtracking fails the test instead of hanging the test run. This
        works on every platform (`signal.SIGALRM` is not available on Windows).
        """

        env = os.environ.copy()
        paths = [os.path.dirname(os.path.dirname(os.path.abspath(sv.__file__)))]
        if env.get('PYTHONPATH'):
            paths.append(env['PYTHONPATH'])
        env['PYTHONPATH'] = os.pathsep.join(paths)

        try:
            result = subprocess.run(
                [sys.executable, '-c', COMPILE_SCRIPT],
                input=pattern,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=env,
                timeout=COMPILE_TIMEOUT
            )
        except subprocess.TimeoutExpired:
            self.fail('Compiling {!r} timed out'.format(pattern[:30] + '...'))

        self.assertEqual(result.returncode, 0, result.stderr)

        with self.assertRaises(sv.SelectorSyntaxError):
            sv.compile(pattern)

    def test_bad_attribute_unclused(self):
        """Test bad attribute fails for syntax error, not timeout error."""

        self.assert_syntax_error_no_timeout('[a="' + ('x' * 300))

    def test_bad_attribute_unclosed_single_quote(self):
        """Test bad attribute with an unclosed single quoted value fails for syntax error, not timeout error."""

        self.assert_syntax_error_no_timeout("[a='" + ('x' * 300))

    def test_bad_attribute_quoted_no_close_bracket(self):
        """Test bad attribute with a quoted value but no closing bracket fails for syntax error, not timeout error."""

        self.assert_syntax_error_no_timeout('[a="' + ('x' * 300) + '"')
        self.assert_syntax_error_no_timeout("[a='" + ('x' * 300) + "'")

    def test_bad_contains_unclosed(self):
        """Test bad `:-soup-contains()` with an unclosed quoted value fails for syntax error, not timeout error."""

        self.assert_syntax_error_no_timeout(':-soup-contains("' + ('x' * 300))
        self.assert_syntax_error_no_timeout(":-soup-contains('" + ('x' * 300))

    def test_bad_lang_unclosed(self):
        """Test bad `:lang()` with an unclosed quoted value fails for syntax error, not timeout error."""

        self.assert_syntax_error_no_timeout(':lang("' + ('x' * 300))
        self.assert_syntax_error_no_timeout(":lang('" + ('x' * 300))
