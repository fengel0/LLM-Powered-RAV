class NotFoundException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class DublicateException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
