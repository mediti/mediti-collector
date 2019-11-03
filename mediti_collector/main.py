#!/usr/bin/env python3
"""Provide the main point of entry."""

import argparse
import contextlib
import datetime
import enum
import math
import pathlib
import re
import threading
from typing import Any, Callable, Optional, Sequence, Tuple

import cv2
import numpy as np

import mediti_collector.announce

_VALID_IDENTIFIER_RE = re.compile(r'^[a-zA-Z-_]+$')


class Arguments:
    """Define command arguments."""

    def __init__(
            self, outdir: pathlib.Path, identifier: str, frequency: float,
            period: float, camera_identifier: int,
            actions: Sequence[str]) -> None:
        """Initialize with the given values."""
        assert _VALID_IDENTIFIER_RE.match(identifier)
        assert frequency > 0
        assert math.isfinite(frequency)
        assert not math.isnan(frequency)
        assert period > 0
        assert math.isfinite(period)
        assert not math.isnan(period)
        assert len(actions) > 0
        assert all(_VALID_IDENTIFIER_RE.match(action) for action in actions)

        self.outdir = outdir
        self.identifier = identifier
        self.frequency = frequency
        self.period = period
        self.camera_identifier = camera_identifier
        self.actions = actions


def parse_command_line_arguments(command_line_args: Any) -> Arguments:
    """Extract the program arguments from the command-line arguments."""
    identifier = str(command_line_args.identifier)
    if not _VALID_IDENTIFIER_RE.match(identifier):
        raise ValueError(
            "Expected identifier matching {!r}, got: {}".format(
                _VALID_IDENTIFIER_RE.pattern, identifier))

    frequency = float(command_line_args.frequency)
    if frequency <= 0.0 or math.isinf(frequency) or math.isnan(frequency):
        raise ValueError(
            "Expected positive and finite frequency, but got: {}".format(
                frequency))

    period = float(command_line_args.period)
    if period <= 0.0 or math.isinf(period) or math.isnan(period):
        raise ValueError(
            "Expected positive and finite period, but got: {}".format(period))

    if len(command_line_args.actions) == 0:
        raise ValueError("Expected at least one action, but got none")

    for action in command_line_args.actions:
        if not _VALID_IDENTIFIER_RE.match(action):
            raise ValueError(
                "Expected action matching {!r}, got: {}".format(
                    _VALID_IDENTIFIER_RE.pattern, action))

    assert isinstance(command_line_args.actions, list)
    assert all(isinstance(action, str) for action in command_line_args.actions)

    return Arguments(
        outdir=pathlib.Path(command_line_args.outdir),
        identifier=identifier,
        frequency=frequency,
        period=period,
        camera_identifier=int(command_line_args.camera),
        actions=command_line_args.actions)


def define_argument_parser() -> argparse.ArgumentParser:
    """Define the parsing of command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Collect training data off-line for mediti.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        "-o",
        "--outdir",
        help="path to the directory where sequence will be recorded; "
        "if it does not exist, it will be created.",
        type=pathlib.Path,
        required=True)

    parser.add_argument(
        "-i",
        "--identifier",
        help="identifier of the recorded sequence",
        type=str,
        required=True)

    parser.add_argument(
        "-f",
        "--frequency",
        help="frequency at which to take the images, in Hz",
        type=float,
        default=1.0)

    parser.add_argument(
        "--period",
        help="period of a single action, in seconds",
        type=float,
        default=7.0)

    parser.add_argument(
        "--camera", help="Camera identifier", type=int, default=0)

    parser.add_argument(
        "--actions",
        help="list of actions to record (duplicates skew the distribution)",
        nargs="+",
        default=["attending", "unattending", "meditating"])

    return parser


class Recording:
    """Manage context of the video stream recording."""

    def __init__(self, capture: cv2.VideoCapture) -> None:
        """
        Initialize the recording with the given values.

        :param frequency: frequency of recorded frames, in Hz
        :param capture:
            initialized video capture.

            The caller should initialize and release the video capture herself.
        """
        self.capture = capture

        self._thread = None  # type: Optional[threading.Thread]
        self._thread_err = None  # type: Optional[Exception]
        self._shutdown = False

        self._frame = None  # type: Optional[np.ndarray]
        self._frame_lock = threading.Lock()

    def __enter__(self) -> 'Recording':
        """Initialize the recording."""
        ...

        # Run capturing in a separate thread
        def run() -> None:
            """Read from the video stream and record a frame if necessary."""
            try:
                while not self._shutdown:
                    ret, frame = self.capture.read()

                    if not ret:
                        raise RuntimeError(
                            "read() from VideoCapture returned False")

                    with self._frame_lock:
                        self._frame = frame

            except Exception as err:  # pylint: disable=broad-except
                self._thread_err = err

        self._thread = threading.Thread(target=run)
        self._thread.start()

        return self

    def copy_frame(self) -> Optional[np.ndarray]:
        """
        Create a copy of the latest recorded frame.

        :return:
            copy of the latest frame, or None if no frame has been recorded yet
        """
        result = None  # type: Optional[np.ndarray]

        with self._frame_lock:
            if self._frame is None:
                result = None
            else:
                result = self._frame.copy()

        return result

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Deconstruct the recording."""
        self._shutdown = True

        if self._thread is not None:
            self._thread.join()

        if self._thread_err:
            raise self._thread_err


class Action:
    """Represent a recordable action."""

    def __init__(self, value: str) -> None:
        """Initialize with the given value."""
        self.value = value


def next_action(
        actions: Sequence[Action], prev_action: Optional[Action]) -> Action:
    """
    Choose the next action to record.

    :param actions: all recordable actions
    :param prev_action: previous recorded action
    :return: next action to be recorded
    """
    assert len(actions) > 0
    assert prev_action is None or prev_action in actions

    if prev_action is None:
        result = actions[0]
    else:
        prev_i = -1
        for i, action in enumerate(actions):
            if action == prev_action:
                prev_i = i
                break

        assert prev_i >= 0
        i = (prev_i + 1) % len(actions)
        result = actions[i]

    return result


def q_or_closed() -> bool:
    """Wait a millisecond for 'q' to be pressed and check if window closed."""
    result = (
        cv2.waitKey(1) & 0xFF == ord('q')
        or cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1)

    assert isinstance(result, bool)
    return result


class State(enum.Enum):
    """Represent the state of the state machine."""

    FADE = 0
    RECORDING = 1
    EXIT = 2


WINDOW_NAME = "mediti-collector"


class Viewer:
    """Display the information to the user on the screen."""

    def __init__(self, recording: Recording) -> None:
        """Initialize with the given recording."""
        self.recording = recording

    def display_fade(self, action: Action) -> None:
        """
        Signal to the user the next action to be recorded.

        :param action: action to be recorded next
        :return:
        """
        frame = self.recording.copy_frame()

        if frame is None:
            frame = np.zeros((200, 200, 3), np.uint8)

        cv2.circle(frame, (10, 19), 5, (255, 255, 255))
        cv2.putText(
            img=frame,
            text="{} (q to quit)".format(action.value),
            org=(25, 25),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=0.5,
            color=(255, 255, 255),
            lineType=2)

        cv2.imshow(WINDOW_NAME, frame)

    def display_recording(self, action: Action) -> None:
        """
        Signal to the user that the video is being recorded.

        :param recording: handles video stream
        :param action: that is recorded
        :return:
        """
        frame = self.recording.copy_frame()
        if frame is None:
            frame = np.zeros((200, 200, 3), np.uint8)

        cv2.circle(frame, (10, 19), 5, (255, 255, 255), -1)
        cv2.putText(
            img=frame,
            text="{} (q to quit)".format(action.value),
            org=(25, 25),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=0.5,
            color=(255, 255, 255),
            lineType=2)

        cv2.imshow(WINDOW_NAME, frame)


def do_fade(
        actions: Sequence[Action], action: Optional[Action],
        announcer: mediti_collector.announce.Announcer, viewer: Viewer,
        exit_fn: Callable[[], bool]) -> Tuple[Action, State]:
    """
    Handle the FADE state: sample the new action and announce it.

    :param actions: all recordable actions
    :param action: last recorded action, if available
    :param announcer: announces the messages
    :param viewer: renders the view for the user
    :param exit_fn: signals that the state should be abandoned
    :return: new action, new state
    """
    prev_action = action
    action = next_action(actions=actions, prev_action=prev_action)

    if prev_action is None:
        announcement = "Let's start with: {}. 1. 2. 3. Go!".format(action.value)
    else:
        announcement = "Thanks! Now let's do: {}. 1. 2. 3. Go!".format(
            action.value)

    with contextlib.ExitStack() as exit_stack:
        exit_stack.callback(announcer.stop)  # pylint: disable=no-member

        announcer.say(text=announcement)

        should_exit = False

        while not announcer.done() and not should_exit:
            viewer.display_fade(action=action)

            if exit_fn():
                should_exit = True

        if should_exit:
            state = State.EXIT
        else:
            state = State.RECORDING

    return action, state


def do_recording(
        action_period: datetime.timedelta, frame_period: datetime.timedelta,
        action: Action, viewer: Viewer, exit_fn: Callable[[], bool],
        utcnow_fn: Callable[[], datetime.datetime],
        store_fn: Callable[[Action, datetime.datetime], None]) -> State:
    """
    Handle the recording state by storing the frame every ``frame_period``.

    :param action_period: duration of the recorded action
    :param frame_period: storage frame rate
    :param action: action that is recorded
    :param viewer: renders the view for the user
    :param exit_fn: signals that the state should be abandoned
    :param utcnow_fn: provides the current time
    :param store_fn: stores the frame at the given ``frame_period``'s
    :return: the new state
    """
    assert action_period > datetime.timedelta(0)
    assert frame_period > datetime.timedelta(0)

    done = False
    should_exit = False

    recording_start = utcnow_fn()
    last_recording = None  # type: Optional[datetime.datetime]

    while not done:
        now = utcnow_fn()
        if now - recording_start >= action_period:
            done = True
        elif exit_fn():
            done = True
            should_exit = True
        else:
            if (last_recording is None or now - last_recording > frame_period):
                last_recording = now
                store_fn(action, now)

        viewer.display_recording(action=action)

    if should_exit:
        state = State.EXIT
    else:
        state = State.FADE

    return state


def execute_state_machine(
        actions: Sequence[Action],
        announcer: mediti_collector.announce.Announcer, viewer: Viewer,
        action_period: datetime.timedelta, frame_period: datetime.timedelta,
        store_fn: Callable[[Action, datetime.datetime], None],
        exit_fn: Callable[[], bool]) -> None:
    """
    Execute the state machine by going through the states.

    :param actions: all recordable actions
    :param announcer: text-to-speech announcer
    :param action_period: the duration of the action recording
    :param frame_period: period between two recorded frames
    :param store_fn: stores the frame
    :param exit_fn: signals that the machine should stop
    :return:
    """
    action = None  # type: Optional[Action]

    state = State.FADE

    while state != State.EXIT:
        if state == State.FADE:
            action, state = do_fade(
                actions=actions,
                action=action,
                announcer=announcer,
                viewer=viewer,
                exit_fn=exit_fn)

        elif state == State.RECORDING:
            assert action is not None, \
                "Expected action to be set before recording"

            state = do_recording(
                action_period=action_period,
                frame_period=frame_period,
                action=action,
                viewer=viewer,
                exit_fn=exit_fn,
                utcnow_fn=datetime.datetime.utcnow,
                store_fn=store_fn)

        else:
            raise NotImplementedError("Unhandled state: {}".format(state))


def main() -> int:
    """Execute the main routine."""
    parser = define_argument_parser()
    cmd_line_args = parser.parse_args()

    args = parse_command_line_arguments(command_line_args=cmd_line_args)

    args.outdir.mkdir(exist_ok=True, parents=True)

    cap = None  # type: Optional[cv2.VideoCapture]

    try:
        ##
        # Initialization
        ##

        announcer = mediti_collector.announce.Announcer()

        cap = cv2.VideoCapture(args.camera_identifier)

        actions = [Action(value=an_action) for an_action in args.actions]

        with announcer, Recording(capture=cap) as recording:
            viewer = Viewer(recording=recording)

            def store_fn(an_action: Action, utcnow: datetime.datetime) -> None:
                """Store the image on disk."""
                pth = args.outdir / "{}.{}.{}.jpg".format(
                    args.identifier, utcnow.strftime("%Y-%m-%dT%H-%M-%S.%fZ"),
                    an_action.value)

                frame = recording.copy_frame()
                cv2.imwrite(str(pth), frame)
                print("Stored to: {}".format(pth))

            ##
            # Execute the state machine
            ##

            execute_state_machine(
                actions=actions,
                viewer=viewer,
                announcer=announcer,
                action_period=datetime.timedelta(seconds=args.period),
                frame_period=datetime.timedelta(seconds=1.0 / args.frequency),
                store_fn=store_fn,
                exit_fn=q_or_closed)

    finally:
        if cap is not None:
            cap.release()

        cv2.destroyAllWindows()

    return 0
