class pixel:
    GOOD = 0
    DO_NOT_USE = 1
    DEAD = 2
    HOT = 4
    WARM = 8
    LOW_QE = 16
    EARLY_SATURATION = 32
    RC = 64
    HIGH_RESET = 128
    HARD_SATURATED = 256
    COSMIC_BEFORE = 512
    FRAMES_SKIPPED = 1024

class group:
    GOOD = 0
    DO_NOT_USE = 1
    ADC_SATURATED = 2
    HARD_SATURATED = 4
    SOFT_SATURATED = 8
    COSMIC_BEFORE = 16
    COSMIC_WITHIN = 32
    AFTER_COSMIC = 64
    RESET_ANOMALY = 128
