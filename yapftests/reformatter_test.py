# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for yapf.reformatter."""

import sys
import textwrap
import unittest

from yapf.yapflib import blank_line_calculator
from yapf.yapflib import comment_splicer
from yapf.yapflib import py3compat
from yapf.yapflib import pytree_unwrapper
from yapf.yapflib import pytree_utils
from yapf.yapflib import pytree_visitor
from yapf.yapflib import reformatter
from yapf.yapflib import split_penalty
from yapf.yapflib import style
from yapf.yapflib import subtype_assigner


class SingleLineReformatterTest(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    style.SetGlobalStyle(style.CreateGoogleStyle())

  def testSimple(self):
    unformatted_code = textwrap.dedent("""\
        if a+b:
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        if a + b:
          pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSimpleFunctions(self):
    unformatted_code = textwrap.dedent("""\
        def g():
          pass

        def f():
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def g():
          pass


        def f():
          pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSimpleFunctionsWithTrailingComments(self):
    unformatted_code = textwrap.dedent("""\
        def g():  # Trailing comment
          if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
              xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
            pass

        def f(  # Intermediate comment
        ):
          if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
              xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def g():  # Trailing comment
          if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
              xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
            pass


        def f(  # Intermediate comment
        ):
          if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
              xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testLineContinuation(self):
    unformatted_code = textwrap.dedent("""\
        x = {  'a':37,'b':42,

        'c':927}

        y = 'hello ''world'
        z = 'hello '+'world'
        a = 'hello {}'.format('world')
        class foo  (     object  ):
          def f    (self   ):
            return       \\
        37*-+2
          def g(self, x,y=42):
              return y
        def f  (   a ) :
          return      37+-+a[42-x :  y**3]
        """)
    expected_formatted_code = textwrap.dedent("""\
        x = {'a': 37, 'b': 42, 'c': 927}

        y = 'hello ' 'world'
        z = 'hello ' + 'world'
        a = 'hello {}'.format('world')


        class foo(object):

          def f(self):
            return 37 * -+2

          def g(self, x, y=42):
            return y


        def f(a):
          return 37 + -+a[42 - x:y ** 3]
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testComments(self):
    unformatted_code = textwrap.dedent("""\
        class Foo(object):
          pass
        # End class Foo

        # Attached comment
        class Bar(object):
          pass

        # Intermediate comment

        class Qux(object):
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        class Foo(object):
          pass
        # End class Foo


        # Attached comment
        class Bar(object):
          pass

        # Intermediate comment


        class Qux(object):
          pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testDocstrings(self):
    unformatted_code = textwrap.dedent('''\
        u"""Module-level docstring."""
        import os
        class Foo(object):

          """Class-level docstring."""
          # A comment for qux.
          def qux(self):


            """Function-level docstring.

            A multiline function docstring.
            """
            print('hello {}'.format('world'))
            return 42
        ''')
    expected_formatted_code = textwrap.dedent('''\
        u"""Module-level docstring."""
        import os


        class Foo(object):
          """Class-level docstring."""

          # A comment for qux.
          def qux(self):
            """Function-level docstring.

            A multiline function docstring.
            """
            print('hello {}'.format('world'))
            return 42
        ''')
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testDocstringAndMultilineComment(self):
    unformatted_code = textwrap.dedent('''\
        """Hello world"""
        # A multiline
        # comment
        class bar(object):
          """class docstring"""
          # class multiline
          # comment
          def foo(self):
            """Another docstring."""
            # Another multiline
            # comment
            pass
        ''')
    expected_formatted_code = textwrap.dedent('''\
        """Hello world"""


        # A multiline
        # comment
        class bar(object):
          """class docstring"""

          # class multiline
          # comment
          def foo(self):
            """Another docstring."""
            # Another multiline
            # comment
            pass
        ''')
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testMultilineDocstringAndMultilineComment(self):
    unformatted_code = textwrap.dedent('''\
        """Hello world

        RIP Dennis Richie.
        """
        # A multiline
        # comment
        class bar(object):
          """class docstring

          A classy class.
          """
          # class multiline
          # comment
          def foo(self):
            """Another docstring.

            A functional function.
            """
            # Another multiline
            # comment
            pass
        ''')
    expected_formatted_code = textwrap.dedent('''\
        """Hello world

        RIP Dennis Richie.
        """


        # A multiline
        # comment
        class bar(object):
          """class docstring

          A classy class.
          """

          # class multiline
          # comment
          def foo(self):
            """Another docstring.

            A functional function.
            """
            # Another multiline
            # comment
            pass
        ''')
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testTupleCommaBeforeLastParen(self):
    unformatted_code = textwrap.dedent("""\
        a = ( 1, )
        """)
    expected_formatted_code = textwrap.dedent("""\
        a = (1,)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testNoBreakOutsideOfBracket(self):
    # FIXME(morbo): How this is formatted is not correct. But it's syntactically
    # correct.
    unformatted_code = textwrap.dedent("""\
        def f():
          assert port >= minimum, \
'Unexpected port %d when minimum was %d.' % (port, minimum)
        """)
    expected_formatted_code = textwrap.dedent("""\
        def f():
          assert port >= minimum, 'Unexpected port %d when minimum was %d.' % (port,
                                                                               minimum)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testBlankLinesBeforeDecorators(self):
    unformatted_code = textwrap.dedent("""\
        @foo()
        class A(object):
          @bar()
          @baz()
          def x(self):
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        @foo()
        class A(object):

          @bar()
          @baz()
          def x(self):
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testOpeningAndClosingBrackets(self):
    unformatted_code = textwrap.dedent("""\
        foo( ( 1, 2, 3, ) )
        """)
    expected_formatted_code = textwrap.dedent("""\
        foo((1, 2, 3,))
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSingleLineFunctions(self):
    unformatted_code = textwrap.dedent("""\
        def foo():  return 42
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo():
          return 42
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testNoQueueSeletionInMiddleOfLine(self):
    # If the queue isn't properly consttructed, then a token in the middle of
    # the line may be selected as the one with least penalty. The tokens after
    # that one are then splatted at the end of the line with no formatting.
    # FIXME(morbo): The formatting here isn't ideal.
    unformatted_code = textwrap.dedent("""\
        find_symbol(node.type) + "< " + " ".join(find_pattern(n) for n in \
node.child) + " >"
        """)
    expected_formatted_code = textwrap.dedent("""\
        find_symbol(node.type) + "< " + " ".join(find_pattern(n)
                                                 for n in node.child) + " >"
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testNoSpacesBetweenSubscriptsAndCalls(self):
    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaa = bbbbbbbb.ccccccccc() [42] (a, 2)
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaa = bbbbbbbb.ccccccccc()[42](a, 2)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testNoSpacesBetweenOpeningBracketAndStartingOperator(self):
    # Unary operator.
    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaa = bbbbbbbb.ccccccccc[ -1 ]( -42 )
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaa = bbbbbbbb.ccccccccc[-1](-42)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    # Varargs and kwargs.
    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaa = bbbbbbbb.ccccccccc( *varargs )
        aaaaaaaaaa = bbbbbbbb.ccccccccc( **kwargs )
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaa = bbbbbbbb.ccccccccc(*varargs)
        aaaaaaaaaa = bbbbbbbb.ccccccccc(**kwargs)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testMultilineCommentReformatted(self):
    unformatted_code = textwrap.dedent("""\
        if True:
            # This is a multiline
            # comment.
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          # This is a multiline
          # comment.
          pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testDictionaryMakerFormatting(self):
    unformatted_code = textwrap.dedent("""\
        _PYTHON_STATEMENTS = frozenset({
            lambda x, y: 'simple_stmt': 'small_stmt', 'expr_stmt': 'print_stmt', 'del_stmt':
            'pass_stmt', lambda: 'break_stmt': 'continue_stmt', 'return_stmt': 'raise_stmt',
            'yield_stmt': 'import_stmt', lambda: 'global_stmt': 'exec_stmt', 'assert_stmt':
            'if_stmt', 'while_stmt': 'for_stmt',
        })
        """)
    expected_formatted_code = textwrap.dedent("""\
        _PYTHON_STATEMENTS = frozenset({
            lambda x, y: 'simple_stmt': 'small_stmt',
            'expr_stmt': 'print_stmt',
            'del_stmt': 'pass_stmt',
            lambda: 'break_stmt': 'continue_stmt',
            'return_stmt': 'raise_stmt',
            'yield_stmt': 'import_stmt',
            lambda: 'global_stmt': 'exec_stmt',
            'assert_stmt': 'if_stmt',
            'while_stmt': 'for_stmt',
        })
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSimpleMultilineCode(self):
    unformatted_code = textwrap.dedent("""\
        if True:
          aaaaaaaaaaaaaa.bbbbbbbbbbbbbb.ccccccc(zzzzzzzzzzzz, \
xxxxxxxxxxx, yyyyyyyyyyyy, vvvvvvvvv)
          aaaaaaaaaaaaaa.bbbbbbbbbbbbbb.ccccccc(zzzzzzzzzzzz, \
xxxxxxxxxxx, yyyyyyyyyyyy, vvvvvvvvv)
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          aaaaaaaaaaaaaa.bbbbbbbbbbbbbb.ccccccc(zzzzzzzzzzzz, xxxxxxxxxxx, yyyyyyyyyyyy,
                                                vvvvvvvvv)
          aaaaaaaaaaaaaa.bbbbbbbbbbbbbb.ccccccc(zzzzzzzzzzzz, xxxxxxxxxxx, yyyyyyyyyyyy,
                                                vvvvvvvvv)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testMultilineComment(self):
    code = textwrap.dedent("""\
        if Foo:
          # Hello world
          # Yo man.
          # Yo man.
          # Yo man.
          # Yo man.
          a = 42
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testMultilineString(self):
    code = textwrap.dedent("""\
        code = textwrap.dedent('''\
            if Foo:
              # Hello world
              # Yo man.
              # Yo man.
              # Yo man.
              # Yo man.
              a = 42
            ''')
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

    unformatted_code = textwrap.dedent('''\
        def f():
            email_text += """<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
        <b>Czar: </b>"""+despot["Nicholas"]+"""<br>
        <b>Minion: </b>"""+serf["Dmitri"]+"""<br>
        <b>Residence: </b>"""+palace["Winter"]+"""<br>
        </body>
        </html>"""
        ''')
    expected_formatted_code = textwrap.dedent('''\
        def f():
          email_text += """<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
        <b>Czar: </b>""" + despot["Nicholas"] + """<br>
        <b>Minion: </b>""" + serf["Dmitri"] + """<br>
        <b>Residence: </b>""" + palace["Winter"] + """<br>
        </body>
        </html>"""
        ''')
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSimpleMultilineWithComments(self):
    code = textwrap.dedent("""\
        if (  # This is the first comment
            a and  # This is the second comment
            # This is the third comment
            b):  # A trailing comment
          # Whoa! A normal comment!!
          pass  # Another trailing comment
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testMatchingParenSplittingMatching(self):
    unformatted_code = textwrap.dedent("""\
        def f():
          raise RuntimeError('unable to find insertion point for target node',
                             (target,))
        """)
    expected_formatted_code = textwrap.dedent("""\
        def f():
          raise RuntimeError('unable to find insertion point for target node',
                             (target,))
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testContinuationIndent(self):
    unformatted_code = textwrap.dedent('''\
        class F:
          def _ProcessArgLists(self, node):
            """Common method for processing argument lists."""
            for child in node.children:
              if isinstance(child, pytree.Leaf):
                self._SetTokenSubtype(
                    child, subtype=_ARGLIST_TOKEN_TO_SUBTYPE.get(
                        child.value, format_token.Subtype.NONE))
        ''')
    expected_formatted_code = textwrap.dedent('''\
        class F:

          def _ProcessArgLists(self, node):
            """Common method for processing argument lists."""
            for child in node.children:
              if isinstance(child, pytree.Leaf):
                self._SetTokenSubtype(child,
                                      subtype=_ARGLIST_TOKEN_TO_SUBTYPE.get(
                                          child.value, \
format_token.Subtype.NONE))
        ''')
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testTrailingCommaAndBracket(self):
    unformatted_code = textwrap.dedent('''\
        a = { 42, }
        b = ( 42, )
        c = [ 42, ]
        ''')
    expected_formatted_code = textwrap.dedent('''\
        a = {42,}
        b = (42,)
        c = [42,]
        ''')
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testI18n(self):
    code = textwrap.dedent("""\
        N_('Some years ago - never mind how long precisely - having little or no money in my purse, and nothing particular to interest me on shore, I thought I would sail about a little and see the watery part of the world.')  # A comment is here.
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

    code = textwrap.dedent("""\
        foo('Fake function call')  #. Some years ago - never mind how long precisely - having little or no money in my purse, and nothing particular to interest me on shore, I thought I would sail about a little and see the watery part of the world.
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testClosingBracketIndent(self):
    code = textwrap.dedent('''\
        def f():

          def g():
            while (xxxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz]) == 'aaaaaaaaaaa' and
                   xxxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz].aaaaaaaa[0]) == 'bbbbbbb'
                  ):
              pass
        ''')
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testClosingBracketsInlinedInCall(self):
    unformatted_code = textwrap.dedent("""\
        class Foo(object):

          def bar(self):
            self.aaaaaaaa = xxxxxxxxxxxxxxxxxxx.yyyyyyyyyyyyy(
                self.cccccc.ddddddddd.eeeeeeee,
                options={
                    "forkforkfork": 1,
                    "borkborkbork": 2,
                    "corkcorkcork": 3,
                    "horkhorkhork": 4,
                    "porkporkpork": 5,
                    })
        """)
    expected_formatted_code = textwrap.dedent("""\
        class Foo(object):

          def bar(self):
            self.aaaaaaaa = xxxxxxxxxxxxxxxxxxx.yyyyyyyyyyyyy(
                self.cccccc.ddddddddd.eeeeeeee,
                options={
                    "forkforkfork": 1,
                    "borkborkbork": 2,
                    "corkcorkcork": 3,
                    "horkhorkhork": 4,
                    "porkporkpork": 5,
                })
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testLineWrapInForExpression(self):
    code = textwrap.dedent("""\
        class A:

          def x(self, node, name, n=1):
            for i, child in enumerate(itertools.ifilter(
                lambda c: pytree_utils.NodeName(c) == name, node.pre_order())):
              pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testFunctionCallContinuationLine(self):
    code = textwrap.dedent("""\
        class foo:

          def bar(self, node, name, n=1):
            if True:
              if True:
                return [(aaaaaaaaaa, bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb(
                    cccc, ddddddddddddddddddddddddddddddddddddd))]
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testI18nNonFormatting(self):
    code = textwrap.dedent("""\
        class F(object):

          def __init__(self, fieldname,
                       #. Error message indicating an invalid e-mail address.
                       message=N_('Please check your email address.'), **kwargs):
            pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testNoSpaceBetweenUnaryOpAndOpeningParen(self):
    code = textwrap.dedent("""\
        if ~(a or b):
          pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testCommentBeforeFuncDef(self):
    code = textwrap.dedent("""\
        class Foo(object):

          a = 42

          # This is a comment.
          def __init__(self, xxxxxxx,
                       yyyyy=0,
                       zzzzzzz=None,
                       aaaaaaaaaaaaaaaaaa=False,
                       bbbbbbbbbbbbbbb=False):
            pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testExcessLineCountWithDefaultKeywords(self):
    unformatted_code = textwrap.dedent("""\
        class Fnord(object):
          def Moo(self):
            aaaaaaaaaaaaaaaa = self._bbbbbbbbbbbbbbbbbbbbbbb(
                ccccccccccccc=ccccccccccccc, ddddddd=ddddddd, eeee=eeee,
                fffff=fffff, ggggggg=ggggggg, hhhhhhhhhhhhh=hhhhhhhhhhhhh,
                iiiiiii=iiiiiiiiiiiiii)
        """)
    expected_formatted_code = textwrap.dedent("""\
        class Fnord(object):

          def Moo(self):
            aaaaaaaaaaaaaaaa = self._bbbbbbbbbbbbbbbbbbbbbbb(
                ccccccccccccc=ccccccccccccc,
                ddddddd=ddddddd,
                eeee=eeee,
                fffff=fffff,
                ggggggg=ggggggg,
                hhhhhhhhhhhhh=hhhhhhhhhhhhh,
                iiiiiii=iiiiiiiiiiiiii)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSpaceAfterNotOperator(self):
    code = textwrap.dedent("""\
        if not (this and that):
          pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testNoPenaltySplitting(self):
    code = textwrap.dedent("""\
        def f():
          if True:
            if True:
              python_files.extend(os.path.join(filename, f)
                                  for f in os.listdir(filename)
                                  if IsPythonFile(os.path.join(filename, f)))
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testExpressionPenalties(self):
    code = textwrap.dedent("""\
      def f():
        if ((left.value == '(' and right.value == ')') or
            (left.value == '[' and right.value == ']') or
            (left.value == '{' and right.value == '}')):
          return False
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

class BuganizerFixes(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    style.SetGlobalStyle(style.CreateGoogleStyle())

  def testB19547210(self):
    code = textwrap.dedent("""\
        while True:
          if True:
            if True:
              if True:
                if xxxxxxxxxxxx.yyyyyyy(aa).zzzzzzz() not in (
                    xxxxxxxxxxxx.yyyyyyyyyyyyyy.zzzzzzzz,
                    xxxxxxxxxxxx.yyyyyyyyyyyyyy.zzzzzzzz):
                  continue
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testB19377034(self):
    code = textwrap.dedent("""\
        def f():
          if (aaaaaaaaaaaaaaa.start >= aaaaaaaaaaaaaaa.end or
              bbbbbbbbbbbbbbb.start >= bbbbbbbbbbbbbbb.end):
            return False
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testB19372573(self):
    code = textwrap.dedent("""\
        def f():
          if a: return 42
          while True:
            if b: continue
            if c: break
          return 0
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testB19353268(self):
    code = textwrap.dedent("""\
        a = {1, 2, 3}[x]
        b = {'foo': 42, 'bar': 37}['foo']
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testB19287512(self):
    unformatted_code = textwrap.dedent("""\
        class Foo(object):

          def bar(self):
            with xxxxxxxxxx.yyyyy(
                'aaaaaaa.bbbbbbbb.ccccccc.dddddddddddddddddddd.eeeeeeeeeee',
                fffffffffff=(aaaaaaa.bbbbbbbb.ccccccc.dddddddddddddddddddd
                             .Mmmmmmmmmmmmmmmmmm(-1, 'permission error'))):
              self.assertRaises(nnnnnnnnnnnnnnnn.ooooo, ppppp.qqqqqqqqqqqqqqqqq)
        """)
    expected_formatted_code = textwrap.dedent("""\
        class Foo(object):

          def bar(self):
            with xxxxxxxxxx.yyyyy(
                'aaaaaaa.bbbbbbbb.ccccccc.dddddddddddddddddddd.eeeeeeeeeee',
                fffffffffff=(
                    aaaaaaa.bbbbbbbb.ccccccc.dddddddddddddddddddd.Mmmmmmmmmmmmmmmmmm(
                        -1, 'permission error')
                )):
              self.assertRaises(nnnnnnnnnnnnnnnn.ooooo, ppppp.qqqqqqqqqqqqqqqqq)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB19194420(self):
    unformatted_code = textwrap.dedent("""\
        method.Set(
            'long argument goes here that causes the line to break',
            lambda arg2=0.5: arg2)
        """)
    expected_formatted_code = textwrap.dedent("""\
        method.Set('long argument goes here that causes the line to break',
                   lambda arg2=0.5: arg2)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB19073499(self):
    code = textwrap.dedent("""\
        instance = (aaaaaaa.bbbbbbb().ccccccccccccccccc().ddddddddddd(
            {'aa': 'context!'}).eeeeeeeeeeeeeeeeeee(
            {  # Inline comment about why fnord has the value 6.
                'fnord': 6
            }))
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testB18257115(self):
    unformatted_code = textwrap.dedent("""\
        if True:
          if True:
             self._Test(
                 aaaa, bbbbbbb.cccccccccc, dddddddd, eeeeeeeeeee,
                 [ffff, ggggggggggg, hhhhhhhhhhhh, iiiiii, jjjj])
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          if True:
            self._Test(aaaa, bbbbbbb.cccccccccc, dddddddd, eeeeeeeeeee,
                       [ffff, ggggggggggg, hhhhhhhhhhhh, iiiiii, jjjj])
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB18256666(self):
    code = textwrap.dedent("""\
        class Foo(object):

          def Bar(self):
            aaaaa.bbbbbbb(ccc='ddddddddddddddd',
                          eeee='ffffffffffffffffffffff-%s-%s' %
                          (gggg, int(time.time())),
                          hhhhhh={
                              'iiiiiiiiiii': iiiiiiiiiii,
                              'jjjj': jjjj.jjjjj(),
                              'kkkkkkkkkkkk': kkkkkkkkkkkk,
                          },
                          llllllllll=mmmmmm.nnnnnnnnnnnnnnnn)
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testB18256826(self):
    code = textwrap.dedent("""\
        if True:
          pass
        # A multiline comment.
        # Line two.
        elif False:
          pass

        if True:
          pass
          # A multiline comment.
          # Line two.
        elif False:
          pass
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testB18255697(self):
    code = textwrap.dedent("""\
        AAAAAAAAAAAAAAA = {
            'XXXXXXXXXXXXXX': 4242,  # Inline comment
            # Next comment
            'YYYYYYYYYYYYYYYY': ['zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'],
        }
        """)
    uwlines = _ParseAndUnwrap(code)
    self.assertEqual(code, reformatter.Reformat(uwlines))

  def testB17534869(self):
    unformatted_code = textwrap.dedent("""\
        if True:
          self.assertLess(abs(time.time()-aaaa.bbbbbbbbbbb(
                              datetime.datetime.now())), 1)
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          self.assertLess(abs(time.time() - aaaa.bbbbbbbbbbb(datetime.datetime.now())),
                          1)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB17489866(self):
    unformatted_code = textwrap.dedent("""\
        def f():
          if True:
            if True:
              return aaaa.bbbbbbbbb(ccccccc=dddddddddddddd({('eeee', \
'ffffffff'): str(j)}))
        """)
    expected_formatted_code = textwrap.dedent("""\
        def f():
          if True:
            if True:
              return aaaa.bbbbbbbbb(
                  ccccccc=dddddddddddddd({('eeee', 'ffffffff'): str(j)}))
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB17133019(self):
    unformatted_code = textwrap.dedent("""\
        class aaaaaaaaaaaaaa(object):

          def bbbbbbbbbb(self):
            with io.open("/dev/null", "rb"):
              with io.open(os.path.join(aaaaa.bbbbb.ccccccccccc,
                                        DDDDDDDDDDDDDDD,
                                        "eeeeeeeee ffffffffff",
                                       ), "rb") as gggggggggggggggggggg:
                print(gggggggggggggggggggg)
        """)
    expected_formatted_code = textwrap.dedent("""\
        class aaaaaaaaaaaaaa(object):

          def bbbbbbbbbb(self):
            with io.open("/dev/null", "rb"):
              with io.open(os.path.join(aaaaa.bbbbb.ccccccccccc, DDDDDDDDDDDDDDD,
                                        "eeeeeeeee ffffffffff",),
                           "rb") as gggggggggggggggggggg:
                print(gggggggggggggggggggg)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB17011869(self):
    unformatted_code = textwrap.dedent("""\
        '''blah......'''

        class SomeClass(object):
          '''blah.'''

          AAAAAAAAAAAA = {                        # Comment.
              'BBB': 1.0,
                'DDDDDDDD': 0.4811
                                      }
        """)
    expected_formatted_code = textwrap.dedent("""\
        '''blah......'''


        class SomeClass(object):
          '''blah.'''

          AAAAAAAAAAAA = {  # Comment.
              'BBB': 1.0,
              'DDDDDDDD': 0.4811
          }
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB16783631(self):
    unformatted_code = textwrap.dedent("""\
        if True:
          with aaaaaaaaaaaaaa.bbbbbbbbbbbbb.ccccccc(ddddddddddddd,
                                                      eeeeeeeee=self.fffffffffffff
                                                      )as gggg:
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          with aaaaaaaaaaaaaa.bbbbbbbbbbbbb.ccccccc(
              ddddddddddddd,
              eeeeeeeee=self.fffffffffffff) as gggg:
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB16572361(self):
    unformatted_code = textwrap.dedent("""\
        def foo(self):
         def bar(my_dict_name):
          self.my_dict_name['foo-bar-baz-biz-boo-baa-baa'].IncrementBy.assert_called_once_with('foo_bar_baz_boo')
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo(self):

          def bar(my_dict_name):
            self.my_dict_name['foo-bar-baz-biz-boo-baa-baa'].IncrementBy.assert_called_once_with(
                'foo_bar_baz_boo')
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB15884241(self):
    unformatted_code = textwrap.dedent("""\
        if 1:
          if 1:
            for row in AAAA:
              self.create(aaaaaaaa="/aaa/bbbb/cccc/dddddd/eeeeeeeeeeeeeeeeeeeeeeeeee/%s" % row [0].replace(".foo", ".bar"), aaaaa=bbb[1], ccccc=bbb[2], dddd=bbb[3], eeeeeeeeeee=[s.strip() for s in bbb[4].split(",")], ffffffff=[s.strip() for s in bbb[5].split(",")], gggggg=bbb[6])
        """)
    expected_formatted_code = textwrap.dedent("""\
        if 1:
          if 1:
            for row in AAAA:
              self.create(aaaaaaaa="/aaa/bbbb/cccc/dddddd/eeeeeeeeeeeeeeeeeeeeeeeeee/%s"
                          % row[0].replace(".foo", ".bar"),
                          aaaaa=bbb[1],
                          ccccc=bbb[2],
                          dddd=bbb[3],
                          eeeeeeeeeee=[s.strip() for s in bbb[4].split(",")],
                          ffffffff=[s.strip() for s in bbb[5].split(",")],
                          gggggg=bbb[6])
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB15697268(self):
    unformatted_code = textwrap.dedent("""\
        def main(unused_argv):
          ARBITRARY_CONSTANT_A = 10
          an_array_with_an_exceedingly_long_name = range(ARBITRARY_CONSTANT_A + 1)
          ok = an_array_with_an_exceedingly_long_name[:ARBITRARY_CONSTANT_A]
          bad_slice = map(math.sqrt, an_array_with_an_exceedingly_long_name[:ARBITRARY_CONSTANT_A])
          a_long_name_slicing = an_array_with_an_exceedingly_long_name[:ARBITRARY_CONSTANT_A]
          bad_slice = ("I am a crazy, no good, string whats too long, etc." + " no really ")[:ARBITRARY_CONSTANT_A]
        """)
    expected_formatted_code = textwrap.dedent("""\
        def main(unused_argv):
          ARBITRARY_CONSTANT_A = 10
          an_array_with_an_exceedingly_long_name = range(ARBITRARY_CONSTANT_A + 1)
          ok = an_array_with_an_exceedingly_long_name[:ARBITRARY_CONSTANT_A]
          bad_slice = map(math.sqrt,
                          an_array_with_an_exceedingly_long_name[:ARBITRARY_CONSTANT_A])
          a_long_name_slicing = an_array_with_an_exceedingly_long_name[:ARBITRARY_CONSTANT_A]
          bad_slice = (
              "I am a crazy, no good, string whats too long, etc." + " no really "
          )[:ARBITRARY_CONSTANT_A]
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB15597568(self):
    unformatted_code = textwrap.dedent("""\
        if True:
          if True:
            if True:
              print(("Return code was %d" + (", and the process timed out." if did_time_out else ".")) % errorcode)
        """)
    expected_formatted_code = textwrap.dedent("""\
        if True:
          if True:
            if True:
              print(("Return code was %d" + (", and the process timed out."
                                             if did_time_out else ".")) % errorcode)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB15542157(self):
    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaaaa = bbbb.ccccccccccccccc(dddddd.eeeeeeeeeeeeee, ffffffffffffffffff, gggggg.hhhhhhhhhhhhhhhhh)
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaaaa = bbbb.ccccccccccccccc(dddddd.eeeeeeeeeeeeee, ffffffffffffffffff,
                                            gggggg.hhhhhhhhhhhhhhhhh)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB15438132(self):
    unformatted_code = textwrap.dedent("""\
        if aaaaaaa.bbbbbbbbbb:
           cccccc.dddddddddd(eeeeeeeeeee=fffffffffffff.gggggggggggggggggg)
           if hhhhhh.iiiii.jjjjjjjjjjjjj:
             # This is a comment in the middle of it all.
             kkkkkkk.llllllllll.mmmmmmmmmmmmm = True
           if (aaaaaa.bbbbb.ccccccccccccc != ddddddd.eeeeeeeeee.fffffffffffff or
               eeeeee.fffff.ggggggggggggggggggggggggggg() != hhhhhhh.iiiiiiiiii.jjjjjjjjjjjj):
             aaaaaaaa.bbbbbbbbbbbb(
                 aaaaaa.bbbbb.cc,
                 dddddddddddd=eeeeeeeeeeeeeeeeeee.fffffffffffffffff(
                     gggggg.hh,
                     iiiiiiiiiiiiiiiiiii.jjjjjjjjjj.kkkkkkk,
                     lllll.mm),
                 nnnnnnnnnn=ooooooo.pppppppppp)
        """)
    expected_formatted_code = textwrap.dedent("""\
        if aaaaaaa.bbbbbbbbbb:
          cccccc.dddddddddd(eeeeeeeeeee=fffffffffffff.gggggggggggggggggg)
          if hhhhhh.iiiii.jjjjjjjjjjjjj:
            # This is a comment in the middle of it all.
            kkkkkkk.llllllllll.mmmmmmmmmmmmm = True
          if (aaaaaa.bbbbb.ccccccccccccc != ddddddd.eeeeeeeeee.fffffffffffff or
              eeeeee.fffff.ggggggggggggggggggggggggggg() !=
              hhhhhhh.iiiiiiiiii.jjjjjjjjjjjj):
            aaaaaaaa.bbbbbbbbbbbb(aaaaaa.bbbbb.cc,
                                  dddddddddddd=eeeeeeeeeeeeeeeeeee.fffffffffffffffff(
                                      gggggg.hh, iiiiiiiiiiiiiiiiiii.jjjjjjjjjj.kkkkkkk,
                                      lllll.mm),
                                  nnnnnnnnnn=ooooooo.pppppppppp)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB14468247(self):
    unformatted_code = textwrap.dedent("""\
        call(a=1,
            b=2,
        )
        """)
    expected_formatted_code = textwrap.dedent("""\
        call(a=1, b=2,)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB14406499(self):
    unformatted_code = textwrap.dedent("""\
        def foo1(parameter_1, parameter_2, parameter_3, parameter_4, \
parameter_5, parameter_6): pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo1(parameter_1, parameter_2, parameter_3, parameter_4, parameter_5,
                 parameter_6):
          pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testB13900309(self):
    unformatted_code = textwrap.dedent("""\
        self.aaaaaaaaaaa(  # A comment in the middle of it all.
               948.0/3600, self.bbb.ccccccccccccccccccccc(dddddddddddddddd.eeee, True))
        """)
    expected_formatted_code = textwrap.dedent("""\
        self.aaaaaaaaaaa(  # A comment in the middle of it all.
            948.0 / 3600, self.bbb.ccccccccccccccccccccc(dddddddddddddddd.eeee, True))
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaa.bbbbbbbbbbbbbbbbbbbbbbbb.cccccccccccccccccccccccccccccc(
            DC_1, (CL - 50, CL), AAAAAAAA, BBBBBBBBBBBBBBBB, 98.0,
            CCCCCCC).ddddddddd(
                # Look! A comment is here.
                AAAAAAAA - (20 * 60 - 5))
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaa.bbbbbbbbbbbbbbbbbbbbbbbb.cccccccccccccccccccccccccccccc(
            DC_1, (CL - 50, CL), AAAAAAAA, BBBBBBBBBBBBBBBB, 98.0,
            CCCCCCC).ddddddddd(  # Look! A comment is here.
            AAAAAAAA - (20 * 60 - 5))
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa.bbbbbbbbbbbbb.ccccccccccccccccccccccccc().dddddddddddddddddddddddddd(1, 2, 3, 4)
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa.bbbbbbbbbbbbb.ccccccccccccccccccccccccc(
        ).dddddddddddddddddddddddddd(1, 2, 3, 4)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa.bbbbbbbbbbbbb.ccccccccccccccccccccccccc(x).dddddddddddddddddddddddddd(1, 2, 3, 4)
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa.bbbbbbbbbbbbb.ccccccccccccccccccccccccc(
            x).dddddddddddddddddddddddddd(1, 2, 3, 4)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa(xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx).dddddddddddddddddddddddddd(1, 2, 3, 4)
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa(
            xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx).dddddddddddddddddddddddddd(1, 2, 3, 4)
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

    unformatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa().bbbbbbbbbbbbbbbbbbbbbbbb().ccccccccccccccccccc().\
dddddddddddddddddd().eeeeeeeeeeeeeeeeeeeee().fffffffffffffffff().gggggggggggggggggg()
        """)
    expected_formatted_code = textwrap.dedent("""\
        aaaaaaaaaaaaaaaaaaaaaaaa().bbbbbbbbbbbbbbbbbbbbbbbb().ccccccccccccccccccc(
        ).dddddddddddddddddd().eeeeeeeeeeeeeeeeeeeee().fffffffffffffffff(
        ).gggggggggggggggggg()
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))


class TestsForPEP8Style(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    style.SetGlobalStyle(style.CreatePEP8Style())

  def testIndent4(self):
    unformatted_code = textwrap.dedent("""\
        if a+b:
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        if a + b:
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testNoBlankBetweenClassAndDef(self):
    unformatted_code = textwrap.dedent("""\
        class Foo:

          def joe():
            pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        class Foo:
            def joe():
                pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testSingleWhiteBeforeTrailingComment(self):
    unformatted_code = textwrap.dedent("""\
        if a+b:  # comment
          pass
        """)
    expected_formatted_code = textwrap.dedent("""\
        if a + b: # comment
            pass
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))


@unittest.skipUnless(py3compat.PY3, 'Requires Python 3')
class TestsForPython3Code(unittest.TestCase):
  """Test a few constructs that are new Python 3 syntax."""

  @classmethod
  def setUpClass(cls):
    style.SetGlobalStyle(style.CreatePEP8Style())

  def testKeywordOnlyArgSpecifier(self):
    unformatted_code = textwrap.dedent("""\
        def foo(a, *, kw):
          return a+kw
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo(a, *, kw):
            return a + kw
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))

  def testAnnotations(self):
    unformatted_code = textwrap.dedent("""\
        def foo(a: list, b: "bar") -> dict:
          return a+b
        """)
    expected_formatted_code = textwrap.dedent("""\
        def foo(a: list, b: "bar") -> dict:
            return a + b
        """)
    uwlines = _ParseAndUnwrap(unformatted_code)
    self.assertEqual(expected_formatted_code, reformatter.Reformat(uwlines))


def _ParseAndUnwrap(code, dumptree=False):
  """Produces unwrapped lines from the given code.

  Parses the code into a tree, performs comment splicing and runs the
  unwrapper.

  Arguments:
    code: code to parse as a string
    dumptree: if True, the parsed pytree (after comment splicing) is dumped
              to stderr. Useful for debugging.

  Returns:
    List of unwrapped lines.
  """
  tree = pytree_utils.ParseCodeToTree(code)
  comment_splicer.SpliceComments(tree)
  subtype_assigner.AssignSubtypes(tree)
  split_penalty.ComputeSplitPenalties(tree)
  blank_line_calculator.CalculateBlankLines(tree)

  if dumptree:
    pytree_visitor.DumpPyTree(tree, target_stream=sys.stderr)

  uwlines = pytree_unwrapper.UnwrapPyTree(tree)
  for uwl in uwlines:
    uwl.CalculateFormattingInformation()

  return uwlines


if __name__ == '__main__':
  unittest.main()
