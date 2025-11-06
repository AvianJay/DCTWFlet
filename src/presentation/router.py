import flet as ft
from typing import Callable, Dict


class Router:
    """Router Manager"""

    def __init__(self, page: ft.Page):
        self.page = page
        self._routes: Dict[str, Callable] = {}
        self._current_route = "/"

    def register(self, route: str, handler: Callable):
        self._routes[route] = handler

    def navigate(self, route: str, **params):
        if route not in self._routes:
            print(f"Route {route} not found")
            return

        self._current_route = route
        self.page.route = route

        view = self._routes[route](**params)

        self.page.clean()
        self.page.add(view)
        self.page.update()

    def go_back(self):
        self.navigate("/")

    @property
    def current_route(self) -> str:
        return self._current_route
