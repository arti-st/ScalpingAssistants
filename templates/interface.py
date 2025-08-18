from mutual_variables.dictionaries import coin_updates


async def update_html():
    # зібрати всі рядки у список словників
    rows = []
    print('Rows in HTML:')
    counter = {}
    for coin, keys in reversed(coin_updates.items()):
        for key, hist in keys.items():
            row = {
                "coin": coin,
                "key": key,
                "upd_time": hist['upd_time'],
                "direction": hist['direction'],
                "min_dist": hist['min_dist'],
                "max_dist": hist['max_dist'],
                "cur_dist": hist['cur_dist'],
                "stable": hist['stable'],
                "min_size": hist['min_size'],
                "max_size": hist['max_size'],
                "cur_size": hist['cur_size'],
            }
            print(row)

            if coin not in counter:
                rows.append(row)
                counter[coin] = 1
            else:
                if counter[coin] <= 5:
                    counter[coin] = 1
                    counter[coin] += 1

    if not rows:
        return

    headers = list(rows[0].keys())

    # будуємо таблицю з фільтрами
    table_html = "<table id='dataTable' class='display' style='width:100%'>\n<thead>\n<tr>"
    for h in headers:
        table_html += f"<th>{h}</th>"
    table_html += "</tr>\n<tr>"
    for _ in headers:
        table_html += "<th><input type='text' placeholder='Filter'></th>"
    table_html += "</tr>\n</thead>\n<tbody>\n"

    for row in rows:
        table_html += "<tr>" + "".join(f"<td>{row[h]}</td>" for h in headers) + "</tr>\n"
    table_html += "</tbody></table>"

    html = f"""
    <html>
    <head>
      <meta charset="utf-8">
      <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
      <script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
      <link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.min.css">
      <script>
        $(document).ready(function() {{
            var table = $('#dataTable').DataTable({{
                orderCellsTop: true,
                fixedHeader: true
            }});
            $('#dataTable thead tr:eq(1) th input').on('keyup change', function() {{
                var index = $(this).parent().index();
                table.column(index).search(this.value).draw();
            }});
        }});
      </script>
    </head>
    <body>
      {table_html}
    </body>
    </html>
    """

    with open('new.html', "w", encoding="utf-8") as f:
        f.write(html)

    print('HTML updated')
