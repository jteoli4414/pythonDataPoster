import numpy as np
import pyqtgraph as pg
import sys

# Generate synthetic data
num_samples = 500
time = np.linspace(0, 10, num_samples, endpoint=False)
signal = np.sin(time) + np.random.normal(size=num_samples) * 0.1
fft_result = np.fft.fft(signal)
freqs = np.fft.fftfreq(num_samples)

pg.plot(freqs[:num_samples//2], np.abs(fft_result)[:num_samples//2], pen='r', name="FFT")  

while True:
    pass