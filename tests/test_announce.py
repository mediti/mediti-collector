#!/usr/bin/env python
# pylint: disable=missing-docstring
# pylint: disable=no-self-use

import os
import time
import unittest

import mediti_collector.announce


@unittest.skipUnless(
    'TEST_WITH_SOUND' in os.environ,
    "Need to enable tests with sound by setting TEST_WITH_SOUND "
    "environment variable")
class TestAnnouncer(unittest.TestCase):
    def test_interruption(self) -> None:
        anno = mediti_collector.announce.Announcer()

        with anno:
            anno.say("hello, " * 20 + "hello!")
            time.sleep(1)

    def test_done(self) -> None:
        anno = mediti_collector.announce.Announcer()

        with anno:
            anno.say("hello")

            start = time.time()
            while not anno.done():
                time.sleep(0.01)

            duration = time.time() - start
            assert duration > 0.5

    def test_two_utterances(self) -> None:
        anno = mediti_collector.announce.Announcer()

        with anno:
            anno.say("hello")

            start = time.time()
            while not anno.done():
                time.sleep(0.01)

            duration = time.time() - start
            assert duration > 0.5

            anno.say("hello again")
            while not anno.done():
                time.sleep(0.01)

            final_duration = time.time() - start
            assert final_duration > 1.0

    def test_say_stop(self) -> None:
        anno = mediti_collector.announce.Announcer()

        with anno:
            anno.say("hello")
            start = time.time()
            time.sleep(0.1)
            anno.stop()

            while not anno.done():
                time.sleep(0.01)
            duration = time.time() - start
            assert duration < 0.3

    def test_say_stop_stay(self) -> None:
        anno = mediti_collector.announce.Announcer()

        with anno:
            anno.say("hello, hello, hello")
            start = time.time()
            time.sleep(0.1)
            anno.stop()

            while not anno.done():
                time.sleep(0.01)
            duration = time.time() - start
            assert duration < 0.4

            anno.say("Hi there!")
            start = time.time()
            while not anno.done():
                time.sleep(0.01)
            duration = time.time() - start
            assert duration > 0.3

    def test_block_on_done(self) -> None:
        anno = mediti_collector.announce.Announcer()

        with anno:
            start = time.time()
            anno.say("hello")
            anno.block_until_done()

            duration = time.time() - start
            assert duration > 0.5


if __name__ == '__main__':
    unittest.main()
