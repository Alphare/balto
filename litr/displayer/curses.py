"""Demo of using urwid with Python 3.4's asyncio.

This code works on older Python 3.x if you install `asyncio` from PyPI, and
even Python 2 if you install `trollius`!
"""
from __future__ import print_function

import random
import asyncio

from contextlib import suppress

import urwid
from urwid import signals


loop = asyncio.get_event_loop()

STATUS = urwid.Text('')
PROGRESS_BAR = urwid.ProgressBar('pg normal', 'pg complete', 0, 1)
FOOTER = urwid.Columns([STATUS, PROGRESS_BAR])
SELECTED_TEST = set()


def on_flagged(name, flagged):
    if flagged:
        SELECTED_TEST.add(name)
    else:
        with suppress(KeyError):
            SELECTED_TEST.remove(name)


class SingleTestWidget(urwid.TreeWidget):

    def __init__(self, *args, **kwargs):
        self.selected_w = urwid.Text('[ ]')
        super().__init__(*args, **kwargs)
        # insert an extra AttrWrap for our own use
        self._w = urwid.AttrWrap(self._w, None)
        self.update_w()

    def selectable(self):
        return True

    def load_inner_widget(self):
        main_w = urwid.Text(self.get_display_text())
        return urwid.Columns(
                [('fixed', 3, self.selected_w), main_w], dividechars=1)

    def keypress(self, size, key):
        """allow subclasses to intercept keystrokes"""
        key = self.__super.keypress(size, key)
        if key:
            key = self.unhandled_keys(size, key)
        return key

    def unhandled_keys(self, size, key):
        """
        Override this method to intercept keystrokes in subclasses.
        Default behavior: Toggle flagged on space, ignore other keys.
        """
        if key == " ":
            self.get_node().toggle_flag()
        else:
            return key

    def update_w(self):
        """Update the attributes of self.widget based on self.flagged.
        """
        data = self.get_node().get_value()
        outcome = data[self.get_node()._key]['outcome']
        self._w.focus_attr = 'focus %s' % outcome
        self._w.attr = outcome

        if self.get_node().flagged:
            self.selected_w.set_text('[x]')
        else:
            self.selected_w.set_text('[ ]')

    def get_display_text(self):
        return self.get_node().get_key()

class SingleTestNode(urwid.TreeNode):

    def __init__(self, *args, flagged=False, test_suite=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.flagged = flagged
        self.test_suite = test_suite

    def toggle_flag(self):
        self.set_flag(not self.flagged)

    def set_flag(self, flag):
        self.flagged = flag
        self.get_widget().update_w()

        on_flagged(self.get_key(), flag)

        self.get_parent().check_flag()

    def load_widget(self):
        return SingleTestWidget(self)

    def refresh(self):
        self.get_widget().update_w()


class TestFileWidget(urwid.TreeWidget):

    unexpanded_icon = urwid.SelectableIcon('▹', 0)
    expanded_icon = urwid.SelectableIcon('▿', 0)

    def __init__(self, *args, **kwargs):
        self.selected_w = urwid.Text('[ ]')
        super().__init__(*args, **kwargs)
        # insert an extra AttrWrap for our own use
        self._w = urwid.AttrWrap(self._w, None)
        self._w.attr = 'body'
        self._w.focus_attr = 'focus'
        self.update_w()

        self.expanded = True
        self.update_expanded_icon()

    def load_inner_widget(self):
        main_w = urwid.Text(self.get_display_text())
        return urwid.Columns(
                [('fixed', 3, self.selected_w), main_w], dividechars=1)

    def get_display_text(self):
        return self.get_node().get_key()

    def selectable(self):
        return True

    def keypress(self, size, key):
        """allow subclasses to intercept keystrokes"""
        key = self.__super.keypress(size, key)
        if key:
            key = self.unhandled_keys(size, key)
        return key

    def unhandled_keys(self, size, key):
        """
        Override this method to intercept keystrokes in subclasses.
        Default behavior: Toggle flagged on space, ignore other keys.
        """
        if key == " ":
            self.get_node().toggle_flag()
        else:
            return key

    def update_w(self):
        """Update the attributes of self.widget based on self.flagged.
        """
        if self.get_node().flagged:
            self.selected_w.set_text('[x]')
        else:
            self.selected_w.set_text('[ ]')


class TestFileNode(urwid.ParentNode):

    def __init__(self, *args, flagged=False, test_suite=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.flagged = flagged
        self.test_suite = test_suite

    def load_widget(self):
        return TestFileWidget(self)

    def load_child_keys(self):
        data = self.get_value()
        return sorted(data.get_tests(test_file=self._key, test_suite=self.test_suite))

    def set_flag(self, flag):
        self.flagged = flag

        for child_key in self.get_child_keys():
            child = self.get_child_node(child_key)
            child.set_flag(flag)

        self.get_widget().update_w()

        if hasattr(self.get_parent(), "check_flag"):
            self.get_parent().check_flag()

    def check_flag(self):
        all_flagged = True
        any_flagged = False

        for child_key in self.get_child_keys():
            child = self.get_child_node(child_key)

            all_flagged = all_flagged and child.flagged
            any_flagged = any_flagged or child.flagged

        if all_flagged:
            self.flagged = True
            self.get_widget().update_w()

            if hasattr(self.get_parent(), "check_flag"):
                self.get_parent().check_flag()

        if not any_flagged:
            self.flagged = False
            self.get_widget().update_w()

            if hasattr(self.get_parent(), "check_flag"):
                self.get_parent().check_flag()

    def toggle_flag(self):
        self.set_flag(not self.flagged)

    def load_child_node(self, key):
        data = self.get_value()

        if 'outcome' in data[key]:
            child_class = SingleTestNode
        else:
            child_class = self.__class__

        return child_class(data, parent=self, key=key, depth=self.get_depth() + 1, flagged=self.flagged,
                           test_suite=self._key)

    def refresh(self):
        # signals.emit_signal(self.get_widget(), "modified")
        self._child_keys = None

        for child_key in self.get_child_keys():
            child = self.get_child_node(child_key)

            child.refresh()


class TestSuiteWidget(urwid.TreeWidget):

    unexpanded_icon = urwid.SelectableIcon('▹', 0)
    expanded_icon = urwid.SelectableIcon('▿', 0)

    def __init__(self, *args, **kwargs):
        self.selected_w = urwid.Text('[ ]')
        super().__init__(*args, **kwargs)
        # insert an extra AttrWrap for our own use
        self._w = urwid.AttrWrap(self._w, None)
        self._w.attr = 'body'
        self._w.focus_attr = 'focus'
        self.update_w()

        self.expanded = True
        self.update_expanded_icon()

    def load_inner_widget(self):
        main_w = urwid.Text(self.get_display_text())
        return urwid.Columns(
                [('fixed', 3, self.selected_w), main_w], dividechars=1)

    def get_display_text(self):
        return "Test suite: " + self.get_node().get_key()

    def selectable(self):
        return True

    def keypress(self, size, key):
        """allow subclasses to intercept keystrokes"""
        key = self.__super.keypress(size, key)
        if key:
            key = self.unhandled_keys(size, key)
        return key

    def unhandled_keys(self, size, key):
        """
        Override this method to intercept keystrokes in subclasses.
        Default behavior: Toggle flagged on space, ignore other keys.
        """
        if key == " ":
            self.get_node().toggle_flag()
        else:
            return key

    def update_w(self):
        """Update the attributes of self.widget based on self.flagged.
        """
        if self.get_node().flagged:
            self.selected_w.set_text('[x]')
        else:
            self.selected_w.set_text('[ ]')


class TestSuiteNode(urwid.ParentNode):

    def __init__(self, *args, flagged=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.flagged = flagged

    def load_widget(self):
        return TestSuiteWidget(self)

    def load_child_keys(self):
        data = self.get_value()
        return sorted(data.get_test_files(test_suite=self._key))

    def set_flag(self, flag):
        self.flagged = flag

        for child_key in self.get_child_keys():
            child = self.get_child_node(child_key)
            child.set_flag(flag)

        self.get_widget().update_w()

        if hasattr(self.get_parent(), "check_flag"):
            self.get_parent().check_flag()

    def check_flag(self):
        all_flagged = True
        any_flagged = False

        for child_key in self.get_child_keys():
            child = self.get_child_node(child_key)

            all_flagged = all_flagged and child.flagged
            any_flagged = any_flagged or child.flagged

        if all_flagged:
            self.flagged = True
            self.get_widget().update_w()

            if hasattr(self.get_parent(), "check_flag"):
                self.get_parent().check_flag()

        if not any_flagged:
            self.flagged = False
            self.get_widget().update_w()

            if hasattr(self.get_parent(), "check_flag"):
                self.get_parent().check_flag()

    def toggle_flag(self):
        self.set_flag(not self.flagged)

    def load_child_node(self, key):
        data = self.get_value()

        child_class = TestFileNode

        return child_class(data, parent=self, key=key, depth=self.get_depth() + 1, flagged=self.flagged)

    def refresh(self):
        # signals.emit_signal(self.get_widget(), "modified")
        self._child_keys = None

        for child_key in self.get_child_keys():
            child = self.get_child_node(child_key)

            child.refresh()


class RootTreeWidget(urwid.TreeWidget):
    """ Display widget for leaf nodes """
    def get_display_text(self):
        return "Tests"


class RootParentNode(urwid.ParentNode):

    def load_widget(self):
        return RootTreeWidget(self)

    def load_child_keys(self):
        data = self.get_value()
        return list(data.get_test_suites())

    def load_child_node(self, key):
        data = self.get_value()
        return TestSuiteNode(data, parent=self, key=key, depth=self.get_depth() + 1)

    def refresh(self):
        # signals.emit_signal(self.get_widget(), "modified")
        self._child_keys = None

        for child_key in self.get_child_keys():
            child = self.get_child_node(child_key)

            child.refresh()


def update_progress_bar(current, total):
    if current >= total:
        PROGRESS_BAR.set_completion(1)
        return

    PROGRESS_BAR.set_completion(current / total)

    loop.call_later(0.5, update_progress_bar, current + 1, total)


PALETTE = [
    ('body', 'black', 'light gray'),
    ('flagged', 'black', 'dark green', ('bold','underline')),
    ('focus', 'light gray', 'dark blue', 'standout'),
    ('focus Passing', 'light green', 'dark blue', 'standout'),
    ('focus Failing', 'light red', 'dark blue', 'standout'),
    ('flagged focus', 'yellow', 'dark cyan',
            ('bold','standout','underline')),
    ('head', 'yellow', 'black', 'standout'),
    ('foot', 'light gray', 'black'),
    ('key', 'light cyan', 'black','underline'),
    ('title', 'white', 'black', 'bold'),
    ('dirmark', 'black', 'dark cyan', 'bold'),
    ('flag', 'dark gray', 'light gray'),
    ('failed', 'dark red', 'light gray'),
    ('passed', 'dark green', 'light gray'),
    ('pg normal',    'white',      'black', 'standout'),
    ('pg complete',  'white',      'dark blue'),
    ('pg smooth', 'dark blue', 'black')
]


class CursesTestDisplayer(object):
    def __init__(self, tests, topnode, walker):
        self.tests = tests
        self.topnode = topnode
        self.walker = walker

        self.test_number = None
        self.current_test_number = 0

    async def parse_message(self, message):
        msg_type = message.get('_type')

        if msg_type == 'session_start':
            self.test_number = message['test_number']
            self.current_test_number = 0
        elif msg_type == 'test_result':
            # Ignore invalid json
            if 'id' not in message or 'outcome' not in message:
                return

            self.tests[message['id']] = message

            test_number = self.current_test_number + 1
            self.current_test_number = test_number

            # Update progress bar
            PROGRESS_BAR.set_completion(float(test_number) / self.test_number)

            self.topnode.refresh()
            self.walker._modified()

        elif msg_type == 'session_end':
            # PROGRESS_BAR.set_completion(0)
            pass
        else:
            raise Exception(message)


class CursesTestInterface(object):

    def __init__(self, repository, eventloop, tests, config, em, runner_class):
        self.repository = repository
        self.eventloop = eventloop
        self.tests = tests
        self.config = config
        self.em = em
        self.runner_class = runner_class

        self.urwid_loop = urwid.MainLoop(
            self._get_urwid_view(),
            PALETTE,
            event_loop=urwid.AsyncioEventLoop(loop=loop),
            unhandled_input=self.unhandled,
        )

        self.displayer = CursesTestDisplayer(self.tests, self.topnode, self.walker)

        # Register the callbacks
        self.em.register(self.displayer.parse_message)

        # def redraw():
        #     self.topnode.refresh()

        #     # Schedule us to update the clock again in one second
        #     loop.call_later(10, redraw)

        # self.eventloop.call_later(10, redraw)

    def _get_urwid_view(self):
        self.topnode = RootParentNode(self.tests)
        self.walker = urwid.TreeWalker(self.topnode)
        listbox = urwid.TreeListBox(self.walker)

        listbox.offset_rows = 1
        footer = urwid.AttrWrap(FOOTER, 'foot')
        return urwid.Frame(
            urwid.AttrWrap(listbox, 'body'),
            footer=footer)

    def run(self):
        self.urwid_loop.run()

    def unhandled(self, key):
        if key in ('ctrl c', 'q'):
            raise urwid.ExitMainLoop
        elif key == 'a':
            c = self.launch_all_tests()
            task = asyncio.ensure_future(c, loop=self.eventloop)

            PROGRESS_BAR.set_completion(0)
            STATUS.set_text("Running all tests")
        elif key == 'r':
            c = self.launch_specific_tests(list(SELECTED_TEST))
            task = asyncio.ensure_future(c, loop=self.eventloop)

            PROGRESS_BAR.set_completion(0)
            STATUS.set_text("Running %s tests" % len(SELECTED_TEST))
        elif key == 'f':
            c = self.launch_failed_tests()
            task = asyncio.ensure_future(c, loop=self.eventloop)

            PROGRESS_BAR.set_completion(0)
            STATUS.set_text("Running %s failing tests" % len(SELECTED_TEST))
        else:
            STATUS.set_text("Key pressed DEBUG: %s" % repr(key))

    async def launch_all_tests(self):
        session = self._get_runner([])
        await session.run()

    async def launch_specific_tests(self, tests):
        session = self._get_runner(tests)
        await session.run()

    async def launch_failed_tests(self):
        tests = self.tests.get_test_by_outcome("failed")
        session = self._get_runner(tests)
        await session.run()

    def _get_runner(self, tests):
        return self.runner_class(self.config, self.repository, self.em, tests,
                                 loop=self.eventloop)