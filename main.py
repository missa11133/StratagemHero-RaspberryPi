import sys

from game.game import Game


if __name__ == "__main__":

    editor_mode = "--edit" in sys.argv
    fullscreen = "--no-fullscreen" not in sys.argv

    # --no-bloom: полностью отключить свечение вокруг текста
    if "--no-bloom" in sys.argv:

        from game.systems import bloom

        bloom.BLOOM_ENABLED = False

    game = Game(editor_mode=editor_mode, fullscreen=fullscreen)
    game.run()