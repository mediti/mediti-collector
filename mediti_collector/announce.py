"""Handle text-to-speech announcements in a multi-processing setting."""
import enum
import multiprocessing
import queue
from typing import Optional

import pyttsx3


class _Code(enum.Enum):
    """Represent command codes to instruct announcer what to do."""

    SAY = 1
    STOP = 2
    TERMINATE = 3


class _Command:
    """Represent a command to the announcer."""

    def __init__(self, code: _Code, text: Optional[str] = None) -> None:
        assert code != _Code.SAY or text is not None, "SAY command needs text."
        assert code == _Code.SAY or text is None, \
            "All commands except SAY do not accept text."

        self.code = code
        self.text = text


class Announcer:
    """Announce messages in a separate process."""

    def __init__(self) -> None:
        """Start the process and initialize the communication."""
        # Inbound queue signaling the text-to-speech engine what to do
        self._command_queue = multiprocessing.Queue(
        )  # type: multiprocessing.Queue[_Command]

        # Outbound queue signaling when the utterance finished
        self._done_queue = multiprocessing.Queue(
        )  # type: multiprocessing.Queue[str]

        # Set to False when the announcement is in progress
        self._done = True

        # pylint: disable=unsubscriptable-object
        def run(
                command_queue: multiprocessing.Queue[_Command],
                done_queue: multiprocessing.Queue[str]) -> None:
            """
            Say the announcements.

            :param command_queue: commands to be executed
            :param done_queue: signal when a message has been announced
            :return:
            """
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.startLoop(useDriverLoop=False)

            message_id = 0

            def on_end(name: str, completed: bool) -> None:
                """Signal that the announcement finished."""
                if completed:
                    done_queue.put(name)

            engine.connect('finished-utterance', on_end)

            while True:
                cmd = None  # type: Optional[_Command]
                try:
                    cmd = command_queue.get(block=False)
                except queue.Empty:
                    pass

                if cmd is not None:
                    if cmd.code == _Code.TERMINATE:
                        engine.endLoop()
                        break

                    elif cmd.code == _Code.STOP:
                        engine.stop()

                    elif cmd.code == _Code.SAY:
                        assert cmd.text is not None, \
                            "SAY command expected to have text."

                        engine.say(text=cmd.text, name=str(message_id))
                        message_id += 1
                    else:
                        raise NotImplementedError(
                            "Unhandled code: {}".format(cmd.code))

                engine.iterate()

        self._process = multiprocessing.Process(
            target=run, args=(self._command_queue, self._done_queue))

        self._process.start()

    def say(self, text: str) -> None:
        """Instruct to say the ``text``."""
        self._done = False
        self._command_queue.put(_Command(code=_Code.SAY, text=text))

    def stop(self) -> None:
        """Instruct to stop the announcement."""
        self._command_queue.put(_Command(code=_Code.STOP))

    def done(self) -> bool:
        """
        Poll whether the announcement has finished.

        :param block: if set, block until the utterance has finished
        :return: True if the utterance has finished
        """
        try:
            self._done_queue.get(block=False)
            self._done = True
        except queue.Empty:
            pass

        return self._done

    def block_until_done(self) -> None:
        """Block until the utterance has finished."""
        self._done_queue.get(block=True)
        self._done = True

    def terminate(self) -> None:
        """Terminate the announcer and join the child process."""
        self._command_queue.put(_Command(code=_Code.TERMINATE))
        self._process.join()

    def __enter__(self) -> 'Announcer':
        """Return the announcer as-is."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Terminate the announcer on context exit."""
        self.terminate()
