import datetime
import sys
import bloomberg
import pandas
import matplotlib
import matplotlib.pyplot as pyplot

from PyQt5 import QtGui, QtWidgets, QtCore, Qt
from io import StringIO


class PreTrade(QtWidgets.QMainWindow):

    def __init__(self):
        super(PreTrade, self).__init__()
        self.portfolio = None
        self.setGeometry(100, 100, 800, 800)
        self.setWindowTitle('PreTrade')
        self.setFixedSize(530, 800)

        headers_list = ['ticker', 'weight']
        self.table_portfolio = QtWidgets.QTableWidget(self)
        self.table_portfolio.resize(300, 780)
        self.table_portfolio.move(10, 10)
        self.table_portfolio.verticalHeader().hide()
        self.table_portfolio.setRowCount(0)
        self.table_portfolio.setColumnCount(len(headers_list))
        self.table_portfolio.setHorizontalHeaderLabels(headers_list)
        for k in range(len(headers_list)):
            self.table_portfolio.horizontalHeader().setSectionResizeMode(k, QtWidgets.QHeaderView.Stretch)

        self.label_start_date = QtWidgets.QLabel('Start Date :', self)
        self.label_start_date.move(315, 10)
        self.input_start_date = QtWidgets.QDateEdit(QtCore.QDate.currentDate().addDays(-55), self)
        self.input_start_date.resize(100, 20)
        self.input_start_date.move(315, 35)

        self.label_end_date = QtWidgets.QLabel('End Date :', self)
        self.label_end_date.move(315, 60)
        self.input_end_date = QtWidgets.QDateEdit(QtCore.QDate.currentDate(), self)
        self.input_end_date.resize(100, 20)
        self.input_end_date.move(315, 85)

        self.button_launch = QtWidgets.QPushButton('Run', self)
        self.button_launch.resize(100, 40)
        self.button_launch.move(420, 16)
        self.button_launch.clicked.connect(self.compute)
        self.button_launch.setStyleSheet('''
        .QPushButton {
            background: rgb(50, 168, 82);
        }
        ''')

        self.button_generate = QtWidgets.QPushButton('Generate\nBasket', self)
        self.button_generate.resize(100, 40)
        self.button_generate.move(420, 66)
        self.button_generate.clicked.connect(self.generate_trade_file)

        self.show()

    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Paste):
            self.paste_basket()

    def paste_basket(self):
        print('test')
        pasted_data = QtWidgets.QApplication.clipboard().text().strip()
        # try:
        if True:
            buffer = StringIO(pasted_data)
            dataframe = pandas.read_csv(buffer, sep=None, engine='python', header=0, index_col=None)
            dataframe.columns = dataframe.columns.map(lambda x: str(x).lower().replace(' ', '_'))
            self.validate_portfolio(dataframe)
        # except:
        #     print('Errors occurred when pasting your data')

    def insert_table_row(self, items, row_height=12):
        row_num = self.table_portfolio.rowCount()
        num_cols = self.table_portfolio.columnCount()
        self.table_portfolio.insertRow(row_num)
        self.table_portfolio.setRowHeight(row_num, row_height)
        for col_num in range(min(num_cols, len(items))):
            self.table_portfolio.setItem(row_num, col_num, items[col_num])

        self.table_portfolio.scrollToItem(self.table_portfolio.item(row_num, 0), QtWidgets.QAbstractItemView.PositionAtTop)
        self.table_portfolio.selectRow(row_num)

    def populate_table(self):
        self.table_portfolio.clearContents()
        self.table_portfolio.setRowCount(0)

        iterator = self.portfolio.iterrows()
        for index, data in iterator:
            ticker = data['ticker']
            weight = data['weight']
            items = [QtWidgets.QTableWidgetItem(str(ticker)), QtWidgets.QTableWidgetItem(str(weight))]
            self.insert_table_row(items, row_height=12)

    def validate_portfolio(self, input_dataframe):
        print(input_dataframe)
        validated_dataframe = input_dataframe.copy(deep=True)
        validated_dataframe['ticker'] = validated_dataframe['ticker'].astype(str)
        validated_dataframe['weight'] = validated_dataframe['weight'].astype(float)
        validated_dataframe = validated_dataframe.groupby(by=['ticker'], as_index=False)['weight'].sum()

        self.portfolio = validated_dataframe
        self.populate_table()

    def compute(self):
        print(self.portfolio)
        if self.portfolio is None:
            return
        elif self.portfolio.shape[0] <= 0:
            return
        else:
            tickers_list = list(self.portfolio.loc[:, 'ticker'].values)
            start_date = str(self.input_start_date.date().toString('yyyyMMdd'))
            end_date = str(self.input_end_date.date().toString('yyyyMMdd'))
            prices = bloomberg.get_hist_data(symbols=tickers_list,
                                             fieldname='PX_LAST',
                                             start_date=start_date,
                                             end_date=end_date,
                                             currency='USD',
                                             adjust_prices=True)

            portfolio = self.portfolio.groupby(by=['ticker'], as_index=True)['weight'].sum()
            long_position = portfolio.loc[portfolio > 0].sum()
            short_position = portfolio.loc[portfolio < 0].sum()
            total_position = max(abs(long_position), abs(short_position))

            prices = prices.loc[:, portfolio.index]
            changes = prices.fillna(method='ffill').fillna(method='bfill').fillna(value=0).pct_change().fillna(value=0)
            pnls = changes.mul(portfolio, axis='columns')
            total_pnl = pnls.sum(axis=1)
            total_return = total_pnl / total_position

            fig, ax = pyplot.subplots(nrows=1, ncols=1, figsize=(10, 7), dpi=80)
            ax.plot(100 * total_return.cumsum(), color='blue', linewidth=1, marker='o', markersize=3)
            ax.axhline(0, color='k', linewidth=1)

            ax.set_title('Generated @ {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')), fontsize=9)
            ax.set_xlabel('Date', fontsize=9, color='grey')
            ax.set_ylabel('Cumulative Return (%)', fontsize=9, color='grey')

            ax.xaxis.grid(color='grey', linestyle='--', linewidth=1, alpha=0.50)
            ax.yaxis.grid(color='grey', linestyle='--', linewidth=1, alpha=0.50)
            for tick in ax.xaxis.get_major_ticks():
                tick.label.set_fontsize(9)
            for tick in ax.yaxis.get_major_ticks():
                tick.label.set_fontsize(9)

            pyplot.show()

    def generate_trade_file(self):
        print('generate trade file')


if __name__ == '__main__':
    QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create('Cleanlooks'))
    if QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication.instance()
    else:
        app = QtWidgets.QApplication(sys.argv)
    window = PreTrade()
    sys.exit(app.exec_())