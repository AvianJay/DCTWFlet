import flet as ft
import config
import threading


def main(page: ft.Page):
    page.title = "DCTW"

    bots_column = ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(),
            ],
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.center,
        expand=True,
    )
    
    servers_column = ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(),
            ],
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.center,
        expand=True,
    )
    
    templates_column = ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(),
            ],
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.center,
        expand=True,
    )
    
    def update_bots(e, force=False):
        bots = config.get_bots(force=force)
        bots_column.content.controls.clear()
        for bot in bots:
            bots_column.content.controls.append(
                ft.ListTile(
                    leading=ft.CircleAvatar(foreground_image_src=config.cache_image(bot["avatar"], size=128)),
                    title=ft.Text(bot["name"]),
                    subtitle=ft.Text(bot["description"]),
                    key=str(bot["id"]),
                    on_click=lambda e: page.go(f"/bot/{e.control.key}"),
                )
            )
        page.update()
    
    def update_servers(e, force=False):
        servers = config.get_servers(force=force)
        servers_column.content.controls.clear()
        for server in servers:
            servers_column.content.controls.append(
                ft.ListTile(
                    leading=ft.CircleAvatar(foreground_image_src=config.cache_image(server["avatar"], size=128)),
                    title=ft.Text(server["name"]),
                    subtitle=ft.Text(server["description"]),
                    key=str(server["id"]),
                    on_click=lambda e: page.go(f"/server/{e.control.key}"),
                )
            )
        page.update()

    def update_templates(e, force=False):
        templates = config.get_templates(force=force)
        templates_column.content.controls.clear()
        for template in templates:
            templates_column.content.controls.append(
                ft.ListTile(
                    title=ft.Text(template["name"]),
                    subtitle=ft.Text(template["description"]),
                    key=str(template["id"]),
                    on_click=lambda e: page.go(f"/template/{e.control.key}"),
                )
            )
        page.update()
    
    def force_update(e):
        type_map = {0: update_bots, 1: update_servers, 2: update_templates}
        index = home_view.navigation_bar.selected_index
        if index in type_map:
            type_map[index](e, force=True)
    
    def show_bot_detail(bot_id):
        bot_view = ft.View(f"/bot/{bot_id}")
        bot_view.scroll = ft.ScrollMode.AUTO
        bot = next((b for b in config.get_bots() if b["id"] == bot_id), None)
        if bot:
            bot_view.appbar = ft.AppBar(
                # title=ft.Text(bot["name"]),
                bgcolor=ft.Colors.TRANSPARENT,
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: page.go("/"),
                ),
                automatically_imply_leading=False,
            )
            bot_view.controls.append(
                ft.Stack(
                    [
                        ft.Container(
                            content=ft.Image(
                                src=config.cache_image(bot["banner"], size=256),
                                fit=ft.ImageFit.FIT_WIDTH,
                            ),
                            height=256,
                            width=page.width,
                        ),
                        ft.Container(
                            content=ft.CircleAvatar(
                                foreground_image_src=config.cache_image(bot["avatar"], size=128),
                                radius=64,
                            ),
                            alignment=ft.alignment.bottom_center,
                            margin=ft.margin.only(top=128),
                        ),
                    ],
                    width=page.width,
                    height=256 + 64,
                ),
            )
            bot_view.controls.append(
                ft.Row(
                    [
                        ft.Text(
                            bot["name"],
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            )
            bot_view.controls.append(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    bot["description"],
                                    size=16,
                                    weight=ft.FontWeight.NORMAL,
                                    text_align=ft.TextAlign.CENTER
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        # inviteLink button
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    icon=ft.Icons.PERSON_ADD,
                                    text="邀請機器人",
                                    on_click=lambda e: page.launch_url(bot["inviteLink"]),
                                ),
                                ft.ElevatedButton(
                                    icon=ft.Icons.HELP_CENTER,
                                    text="支援伺服器",
                                    on_click=lambda e: page.launch_url(bot["serverLink"]),
                                ),
                                ft.ElevatedButton(
                                    icon=ft.Icons.LINK,
                                    text="官方網站",
                                    on_click=lambda e: page.launch_url(bot["webLink"]),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Markdown(
                            bot["introduce"],
                            fit_content=False,
                            on_tap_link=lambda e: page.launch_url(e.data),
                        )
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    scroll=ft.ScrollMode.AUTO,
                )
            )
            page.views.append(bot_view)
            page.update()
        

    def route_change(route):
        page.views.clear()
        if page.route == "/":
            page.views.append(home_view)
        elif page.route == "/about":
            page.views.append(ft.View("/about", [ft.Text("About Page")]))
        elif page.route.startswith("/bot/"):
            bot_id = page.route.split("/bot/")[1]
            show_bot_detail(bot_id)
        else:
            page.views.append(ft.View("/notfound", [ft.Text("404 - Page Not Found")]))
        page.update()
    
    def view_pop(e):
        print("View pop:", e.view)
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)
    
    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    home_view = ft.View("/")
    home_view.appbar = ft.AppBar(
        title=ft.Text("DCTW"),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions=[
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                on_click=force_update,
            )
        ]
    )
    
    def home_show_page(index):
        home_view.controls.clear()
        if index == 0:
            home_view.controls.append(bots_column)
            threading.Thread(target=update_bots, args=(None, False)).start()
        elif index == 1:
            home_view.controls.append(servers_column)
            threading.Thread(target=update_servers, args=(None, False)).start()
        elif index == 2:
            home_view.controls.append(templates_column)
            threading.Thread(target=update_templates, args=(None, False)).start()
        page.update()
    
    def on_nav_change(e):
        home_show_page(e.control.selected_index)
    
    home_view.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.SMART_TOY_OUTLINED,
                selected_icon=ft.Icons.SMART_TOY,
                label="機器人"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.DASHBOARD_OUTLINED,
                selected_icon=ft.Icons.DASHBOARD,
                label="伺服器"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.ARTICLE_OUTLINED,
                selected_icon=ft.Icons.ARTICLE,
                label="伺服器模板"
            ),
        ],
        on_change=on_nav_change
    )
    home_show_page(0)
    page.go("/")


ft.app(main)
