import pygame


class AudioManager:

    MASTER_VOLUME = 0.5
    MUSIC_VOLUME = 0.6 * MASTER_VOLUME
    SFX_VOLUME = 0.6 * MASTER_VOLUME

    # Сколько одновременных эффектов поддерживать
    SFX_CHANNELS = 4

    def __init__(self):

        self.available = True
        self.sounds = {}

        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(self.SFX_CHANNELS)
        except pygame.error:
            # Нет аудиоустройства — игра работает без звука
            self.available = False

    # ==================================================
    # Музыка
    #
    # Играет на выделенном стриме pygame.mixer.music —
    # эффекты (Sound) её не прерывают.
    # ==================================================

    def play_music(self, path):

        if not self.available:
            return

        # Уже играет — не перезапускаем
        if pygame.mixer.music.get_busy():
            return

        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(self.MUSIC_VOLUME)
        pygame.mixer.music.play(-1)   # -1 = бесконечный цикл

    def stop_music(self):

        if self.available:
            pygame.mixer.music.stop()

    # ==================================================
    # Эффекты (будущие звуки стрелок и т.п.)
    #
    # Звук кэшируется и играет поверх музыки на свободном
    # канале микшера, не трогая music-стрим.
    # ==================================================

    def play_sfx(self, path):

        if not self.available:
            return

        if path not in self.sounds:
            self.sounds[path] = pygame.mixer.Sound(path)

        self.sounds[path].set_volume(self.SFX_VOLUME)
        self.sounds[path].play()