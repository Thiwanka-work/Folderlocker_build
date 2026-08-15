import flet as ft
def main(page: ft.Page):
    b = ft.ElevatedButton("INITIAL")
    page.add(b)
    b.content = ft.Text("UPDATED")
    b.update()
    print("DONE with Text")
    try:
        b.content = "STRING UPDATED"
        b.update()
        print("DONE with string")
    except Exception as e:
        print("ERROR with string:", e)
ft.app(target=main)
