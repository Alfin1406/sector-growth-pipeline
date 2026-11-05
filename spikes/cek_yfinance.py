import yfinance as yf

print("Mencoba menarik data emiten BEI (BBCA) via Yahoo Finance...")
# Menggunakan suffix .JK untuk emiten Jakarta (BEI)
bbca = yf.Ticker("BBCA.JK")

# Menarik data riwayat harga 5 hari terakhir
hist = bbca.history(period="5d")

if not hist.empty:
    print("BUKTI FALLBACK BERHASIL: Data OHLC berhasil ditarik secara otomatis!")
    print(hist[['Open', 'Close', 'Volume']])
else:
    print("Gagal menarik data.")