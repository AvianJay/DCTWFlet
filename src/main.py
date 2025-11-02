import flet as ft
import config
import threading


def main(page: ft.Page):
    page.title = "DCTW"
    
    # theme
    def update_theme(theme=config.config("theme")):
        config.config("theme", ft.ThemeMode(theme).value, "w")
        page.theme_mode = ft.ThemeMode(config.config("theme"))
        page.update()
    update_theme()

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
                    leading=ft.CircleAvatar(foreground_image_src=config.cache_image(bot["avatar_url"], size=128)),
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
                    leading=ft.CircleAvatar(foreground_image_src=config.cache_image(server["icon_url"], size=128)),
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
                                src=config.cache_image(bot["banner"], size=1024),
                                fit=ft.ImageFit.FIT_WIDTH,
                            ),
                            height=256,
                            width=page.width,
                        ),
                        ft.Container(
                            content=ft.CircleAvatar(
                                foreground_image_src=config.cache_image(bot["avatar_url"], size=256),
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
            verified = bot.get("verified", False)
            is_partner = bot.get("is_partnered", False)
            bot_view.controls.append(
                ft.Row(
                    [
                        ft.Text(
                            bot["name"],
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER
                        ),
                        *(
                            [ft.ElevatedButton(text="Discord官方驗證", icon=ft.Icons.VERIFIED, bgcolor=ft.Colors.BLUE)] if verified else []
                        ),
                        *(
                            [ft.ElevatedButton(text="DCTW合作夥伴", icon=ft.Icons.STAR, bgcolor=ft.Colors.GREEN)] if is_partner else []
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            )
            tags = bot.get("tags", "").split(",")
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
                                    on_click=lambda e: page.launch_url(bot["invite_url"]),
                                ),
                                ft.ElevatedButton(
                                    icon=ft.Icons.HELP_CENTER,
                                    text="支援伺服器",
                                    on_click=lambda e: page.launch_url(bot["server_url"]),
                                ),
                                ft.ElevatedButton(
                                    icon=ft.Icons.LINK,
                                    text="官方網站",
                                    on_click=lambda e: page.launch_url(bot["web_url"]),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        # tags
                        
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
        else:
            page.open(
                ft.SnackBar(
                    content=ft.Text("找不到此機器人。"),
                )
            )
            page.go("/")
    
    def show_server_detail(server_id):
        server_view = ft.View(f"/server/{server_id}")
        server_view.scroll = ft.ScrollMode.AUTO
        server = next((s for s in config.get_servers() if s["id"] == server_id), None)
        if server:
            server_view.appbar = ft.AppBar(
                title=ft.Text(server["name"]),
                bgcolor=ft.Colors.TRANSPARENT,
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: page.go("/"),
                ),
                automatically_imply_leading=False,
            )
            server_view.controls.append(
                ft.Stack(
                    [
                        ft.Container(
                            content=ft.Image(
                                src=config.cache_image(server["banner_url"], size=1024),
                                fit=ft.ImageFit.FIT_WIDTH,
                            ),
                            width=page.width,
                            height=256,
                        ),
                        ft.Container(
                            content=ft.CircleAvatar(
                                foreground_image_src=config.cache_image(server["icon_url"], size=256),
                                radius=64,
                            ),
                            alignment=ft.alignment.bottom_center,
                            margin=ft.margin.only(top=128),
                        ),
                    ]
                )
            )
            server_view.controls.append(
                ft.Row(
                    [
                        ft.Text(
                            server["name"],
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            )
            server_view.controls.append(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    server["description"],
                                    size=16,
                                    weight=ft.FontWeight.NORMAL,
                                    text_align=ft.TextAlign.CENTER
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    icon=ft.Icons.ADD,
                                    text="加入伺服器",
                                    on_click=lambda e: page.launch_url(server["invite_url"]),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Markdown(
                            server["introduce"],
                            fit_content=False,
                            on_tap_link=lambda e: page.launch_url(e.data),
                        )
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    scroll=ft.ScrollMode.AUTO,
                )
            )
            server_view.controls.append(
                ft.Text("伺服器詳情頁面正在開發中...")
            )
            page.views.append(server_view)
            page.update()
        else:
            page.open(
                ft.SnackBar(
                    content=ft.Text("找不到此伺服器。"),
                )
            )
            page.go("/")
    
    def show_template_detail(template_id):
        template_view = ft.View(f"/template/{template_id}")
        template_view.scroll = ft.ScrollMode.AUTO
        template_id = int(template_id)
        template = next((t for t in config.get_templates() if t["id"] == template_id), None)
        if template:
            template_view.appbar = ft.AppBar(
                title=ft.Text(template["name"]),
                bgcolor=ft.Colors.TRANSPARENT,
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: page.go("/"),
                ),
                automatically_imply_leading=False,
            )
            template_view.controls.append(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    template["name"],
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    text_align=ft.TextAlign.CENTER
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            [
                                ft.Text(
                                    template["description"],
                                    size=16,
                                    weight=ft.FontWeight.NORMAL,
                                    text_align=ft.TextAlign.CENTER
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    icon=ft.Icons.ADD,
                                    text="使用模板",
                                    on_click=lambda e: page.launch_url(template["share_url"]),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Markdown(
                            template["introduce"],
                            on_tap_link=lambda e: page.launch_url(e.data),
                        )
                    ]
                )
            )
            template_view.controls.append(
                ft.Text("伺服器模板詳情頁面正在開發中...")
            )
            page.views.append(template_view)
            page.update()
        else:
            page.open(
                ft.SnackBar(
                    content=ft.Text("找不到此伺服器模板。"),
                )
            )
            page.go("/")
    
    def upload_log(e):
        if config.update_channel == "developer":
            page.open(
                ft.SnackBar(
                    content=ft.Text("developer模式無法上傳。"),
                )
            )
            return
        try:
            url = config.upload_log()
        except Exception as e:
            page.open(
                ft.SnackBar(
                    content=ft.Text(f"上傳錯誤: {str(e)}"),
                )
            )
        page.set_clipboard(url)
        page.open(
            ft.SnackBar(
                content=ft.Text("連結已複製到剪貼簿。"),
                action="開啟網頁",
                on_action=lambda e: page.launch_url(url),
            )
        )
        

    def route_change(route):
        page.views.clear()
        # if page.route == "/":
        page.views.append(home_view)
        if page.route == "/about":
            page.views.append(ft.View("/about", [ft.Text("About Page")]))
        elif page.route.startswith("/bot/"):
            bot_id = page.route.split("/bot/")[1]
            show_bot_detail(bot_id)
        elif page.route.startswith("/server/"):
            server_id = page.route.split("/server/")[1]
            show_server_detail(server_id)
        elif page.route.startswith("/template/"):
            template_id = page.route.split("/template/")[1]
            show_template_detail(template_id)
        elif page.route.startswith("/settings"):
            page.views.append(
                ft.View(
                    "/settings",
                    [
                        ft.AppBar(
                            title=ft.Text("設定"),
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        ),
                        ft.Column(
                            [
                                ft.Dropdown(
                                    label="主題",
                                    options=[
                                        ft.dropdown.Option("system", "系統預設"),
                                        ft.dropdown.Option("light", "淺色主題"),
                                        ft.dropdown.Option("dark", "深色主題"),
                                    ],
                                    value=config.config("theme"),
                                    on_change=lambda e: update_theme(e.control.value),
                                ),
                                ft.Dropdown(
                                    label="應用程式更新通知",
                                    options=[
                                        ft.dropdown.Option("popup", "彈出視窗"),
                                        ft.dropdown.Option("notify", "通知訊息"),
                                        ft.dropdown.Option("none", "不通知"),
                                    ],
                                    value=config.config("app_update_check"),
                                    on_change=lambda e: config.config("app_update_check", e.control.value, "w"),
                                ),
                                # api key
                                ft.Text("dctw.nyanko.host API Key（一般來講無須更改）"),
                                ft.TextField(
                                    label="API Key",
                                    value=config.config("apikey"),
                                    on_change=lambda e: config.config("apikey", e.control.value, "w"),
                                ),
                                # version info
                                ft.Text(f"應用程式版本: {config.full_version}"),
                                ft.ElevatedButton(
                                    text="上傳應用程式日誌",
                                    icon=ft.Icons.BUG_REPORT,
                                    on_click=upload_log,
                                ),
                            ],
                            scroll=ft.ScrollMode.AUTO,
                            alignment=ft.MainAxisAlignment.START,
                        ),
                    ]
                )
            )
        # else:
        #     page.views.append(ft.View("/notfound", [ft.Text("404 - Page Not Found")]))
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
                icon=ft.Icons.SETTINGS,
                on_click=lambda e: page.go("/settings"),
                tooltip="設定",
            ),
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                on_click=force_update,
                tooltip="重新整理",
            ),
        ]
    )
    
    def home_show_page(index):
        home_view.controls.clear()
        config.config("home_index", index, "w")
        if index == 0:
            page.title = "DCTW - 機器人"
            home_view.appbar.title = ft.Text("機器人清單")
            home_view.controls.append(bots_column)
            threading.Thread(target=update_bots, args=(None, False)).start()
        elif index == 1:
            page.title = "DCTW - 伺服器"
            home_view.appbar.title = ft.Text("伺服器清單")
            home_view.controls.append(servers_column)
            threading.Thread(target=update_servers, args=(None, False)).start()
        elif index == 2:
            page.title = "DCTW - 伺服器模板"
            home_view.appbar.title = ft.Text("伺服器模板清單")
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
        selected_index=config.config("home_index", 0),
        on_change=on_nav_change
    )
    home_show_page(config.config("home_index", 0))
    page.go("/")
    
    def open_app_update_dialog(updates, data):
        def app_update(e):
            page.open(ft.SnackBar(
                content=ft.Text("正在更新"),
            ))
            page.launch_url(data)
        upddlg = ft.AlertDialog(
            title=ft.Text("應用程式有新更新"),
            content=ft.Markdown(updates, on_tap_link=lambda e: page.launch_url(e.data)),
            actions=[
                ft.TextButton("下次再說", on_click=lambda e: page.close(upddlg)),
                ft.TextButton("更新", on_click=app_update),
            ],
        )
        page.open(upddlg)
    
    try:
        updates, data = config.check_update()
        if updates:
            home_view.appbar.actions.append(
                ft.IconButton(
                    ft.Icons.UPDATE,
                    on_click=lambda e: open_app_update_dialog(updates, data),
                    tooltip="應用程式有新版本",
                )
            )
            page.update()
            if config.config("app_update_check") == "popup":
                open_app_update_dialog(updates, data)
            elif config.config("app_update_check") == "notify":
                ft.SnackBar(
                    content=ft.Text("應用程式有新版本"),
                    action="查看",
                    on_action=lambda e: open_app_update_dialog(updates, data),
                )
        else:
            if data:
                page.open(ft.SnackBar(
                    content=ft.Text("錯誤: " + data),
                    action="確定",
                ))
    except Exception as e:
        print("Failed to check app update:", str(e))
        page.open(ft.SnackBar(
            content=ft.Text("檢查程式更新時發生錯誤。"),
            action="確定",
        ))
    home_view.appbar.actions.reverse()
    page.update()


ft.app(main)
