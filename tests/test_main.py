#!/usr/bin/env python3

# pylint: disable=missing-docstring
import datetime
import math
import pathlib
import time
import unittest
from typing import List, Optional, Tuple

import mediti_collector.main


class TestArguments(unittest.TestCase):
    def test_invalid_identifier(self) -> None:
        parser = mediti_collector.main.define_argument_parser()
        cmd_line_args = parser.parse_args(
            args=["--outdir", "/some/path", "--identifier", "!some/identifier"])

        got_err = None  # type: Optional[ValueError]
        try:
            mediti_collector.main.parse_command_line_arguments(
                command_line_args=cmd_line_args)
        except ValueError as err:
            got_err = err

        self.assertIsNotNone(got_err)
        self.assertEqual(
            "Expected identifier matching '^[a-zA-Z-_]+$', "
            "got: !some/identifier", str(got_err))

    def test_invalid_frequency(self) -> None:
        freqs = [-1.0, 0.0, math.inf, math.nan]

        for freq in freqs:
            parser = mediti_collector.main.define_argument_parser()
            cmd_line_args = parser.parse_args(
                args=[
                    "--outdir", "/some/path", "--identifier", "some_identifier",
                    "--frequency",
                    str(freq)
                ])

            got_err = None  # type: Optional[ValueError]
            try:
                mediti_collector.main.parse_command_line_arguments(
                    command_line_args=cmd_line_args)
            except ValueError as err:
                got_err = err

            self.assertIsNotNone(got_err)
            self.assertEqual(
                "Expected positive and finite frequency, but got: {}".format(
                    freq), str(got_err))

    def test_invalid_period(self) -> None:
        periods = [-1.0, 0.0, math.inf, math.nan]

        for period in periods:
            parser = mediti_collector.main.define_argument_parser()
            cmd_line_args = parser.parse_args(
                # yapf: disable
                args=[
                    "--outdir", "/some/path", "--identifier", "some_identifier",
                    "--period",
                    str(period)
                ])
            # yapf: enable

            got_err = None  # type: Optional[ValueError]
            try:
                mediti_collector.main.parse_command_line_arguments(
                    command_line_args=cmd_line_args)
            except ValueError as err:
                got_err = err

            self.assertIsNotNone(got_err)
            self.assertEqual(
                "Expected positive and finite period, but got: {}".format(
                    period), str(got_err))

    def test_invalid_actions(self) -> None:
        parser = mediti_collector.main.define_argument_parser()
        cmd_line_args = parser.parse_args(
            # yapf: disable
            args=[
                "--outdir", "/some/path", "--identifier", "some_identifier",
                "--actions", "invalid!action"
            ])
        # yapf: enable

        got_err = None  # type: Optional[ValueError]
        try:
            mediti_collector.main.parse_command_line_arguments(
                command_line_args=cmd_line_args)
        except ValueError as err:
            got_err = err

        self.assertIsNotNone(got_err)
        self.assertEqual(
            "Expected action matching '^[a-zA-Z-_]+$', got: invalid!action",
            str(got_err))

    def test_args_set(self) -> None:
        parser = mediti_collector.main.define_argument_parser()
        cmd_line_args = parser.parse_args(
            # yapf: disable
            args=[
                "--outdir", "/some/path", "--identifier", "some_identifier",
                "--frequency", "2.0", "--period", "198.4", "--actions",
                "an_action", "an_action", "another_action"
            ])
        # yapf: enable

        args = mediti_collector.main.parse_command_line_arguments(
            command_line_args=cmd_line_args)

        self.assertEqual(pathlib.Path("/some/path"), args.outdir)
        self.assertEqual("some_identifier", args.identifier)
        self.assertEqual(2.0, args.frequency)
        self.assertEqual(198.4, args.period)
        self.assertListEqual(['an_action', 'an_action', 'another_action'],
                             args.actions)  # type: ignore


class TestStateMachine(unittest.TestCase):
    def test_that_it_works(self) -> None:
        ##
        # Mock
        ##

        actions = [
            mediti_collector.main.Action(value='an_action'),
            mediti_collector.main.Action(value='another_action')
        ]

        announcement_period = datetime.timedelta(seconds=0.5)

        class MockEngine:
            # pylint: disable=invalid-name
            # pylint: disable=no-self-use
            def __init__(self) -> None:
                self.queue = []  # type: List[str]

            def say(self, text: str) -> None:
                self.queue.append(text)

            def runAndWait(self) -> None:
                time.sleep(announcement_period.total_seconds())
                self.queue.pop()

            def stop(self) -> None:
                self.queue = []

        engine = MockEngine()

        class MockViewer:
            # pylint: disable=unused-argument
            # pylint: disable=no-self-use
            def display_fade(
                    self, action: mediti_collector.main.Action) -> None:
                return

            def display_recording(
                    self, action: mediti_collector.main.Action) -> None:
                return

        viewer = MockViewer()

        stores = []  # type: List[Tuple[str, datetime.datetime]]

        def mock_store_fn(
                action: mediti_collector.main.Action,
                now: datetime.datetime) -> None:
            stores.append((action.value, now))

        execution_start = datetime.datetime.utcnow()

        def mock_exit_fn() -> bool:
            return (
                datetime.datetime.utcnow() - execution_start >
                datetime.timedelta(seconds=5.0))

        ##
        # Execute
        ##

        mediti_collector.main.execute_state_machine(
            actions=actions,
            engine=engine,
            viewer=viewer,  # type: ignore
            action_period=datetime.timedelta(seconds=2),
            frame_period=datetime.timedelta(seconds=0.5),
            store_fn=mock_store_fn,
            exit_fn=mock_exit_fn)

        execution_stop = datetime.datetime.utcnow()

        ##
        # Verify
        ##

        self.assertEqual(8, len(stores))

        _, last_an_action_ts = stores[3]
        _, first_another_action_ts = stores[4]

        for i in range(4):
            action, timestamp = stores[i]
            self.assertEqual('an_action', action)
            self.assertLess(execution_start, timestamp)
            self.assertLess(timestamp, first_another_action_ts)

        for i in range(4, 8):
            action, timestamp = stores[i]
            self.assertEqual('another_action', action)
            self.assertLess(last_an_action_ts, timestamp)
            self.assertLessEqual(timestamp, execution_stop)


if __name__ == '__main__':
    unittest.main()
