
import yfinance as yf

tsla = yf.Ticker("TSLA")
stock_data = tsla.history(period="30d")
import matplotlib.pyplot as plt

plt.figure(figsize=(12,5))
plt.plot(stock_data.index, stock_data['Close'])
plt.title('Tesla Stock Price Over Last 30 Days')
plt.xlabel('Date')
plt.ylabel('Price (USD)')
plt.grid(True)
plt.show()
