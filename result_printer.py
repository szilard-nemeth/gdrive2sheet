from tabulate import tabulate


class ResultPrinter:
    def __init__(self, data, headers):
        self.data = data
        self.headers = headers

    def print_table(self):
        print(tabulate(self.data, self.headers, tablefmt="fancy_grid"))

    def print_table_html(self):
        print(tabulate(self.data, self.headers, tablefmt="html"))
