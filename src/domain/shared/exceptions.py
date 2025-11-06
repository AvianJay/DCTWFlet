from typing import Any


class DomainException(Exception):

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class InvalidArgumentException(DomainException):

    def __init__(self, argument_name: str, message: str = None):
        self.argument_name = argument_name
        msg = message or f"Invalid argument: {argument_name}"
        super().__init__(msg)


class EntityNotFoundException(DomainException):

    def __init__(self, entity_type: str, entity_id: Any):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with id {entity_id} not found")


class BusinessRuleViolationException(DomainException):

    def __init__(self, rule: str, message: str = None):
        self.rule = rule
        msg = message or f"Business rule violated: {rule}"
        super().__init__(msg)
