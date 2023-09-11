import sys
from typing import Any
from types import MethodType


def get_caller() -> type:
    frame = sys._getframe(2)
    arguments = frame.f_code.co_argcount
    if not arguments:
        return None, frame.f_code.co_name
    
    caller_self = frame.f_code.co_varnames[0]
    caller = frame.f_locals[caller_self]
    return caller.__class__, frame.f_code.co_name


def find_defining_class(cls, attribute) -> type:
    for base_class in cls.mro():
        if attribute in base_class.__dict__:
            return base_class
    return None


def _assume_self_strictness(getattribute_method: MethodType, setattribute_method: MethodType, private_member_prefix: str, protected_member_prefix: str):
    def getattribute_wrapper(self, name: str) -> Any:
        if name.startswith("__") and name.endswith("__"):
            return getattribute_method(self, name)

        caller_class, caller_method_name = get_caller()
        is_protected: bool = name.startswith(protected_member_prefix)
        is_private: bool = not is_protected and name.startswith(private_member_prefix)

        defining_class = find_defining_class(type(self), name)
        if caller_class is None:
            if is_protected:
                raise PermissionError(f"Access to protected member \"{name}\" of class \"{defining_class.__name__}\" not allowed.")
            if is_private:
                raise PermissionError(f"Access to private member \"{name}\" of class \"{defining_class.__name__}\" not allowed.")
            return getattribute_method(self, name)

        if is_private and caller_method_name not in dir(defining_class):
            raise PermissionError(f"Access to private member \"{name}\" of class \"{defining_class.__name__}\" not allowed.")
        if is_protected and not issubclass(caller_class, type(self)):
            raise PermissionError(f"Access to protected member \"{name}\" of class \"{defining_class.__name__}\" not allowed.")
        return getattribute_method(self, name)

    def setattr_wrapper(self, name: str, value: Any) -> Any:
        if name.startswith("__") and name.endswith("__"):
            return setattribute_method(self, name, value)
        
        caller_class, caller_method_name = get_caller()
        is_protected: bool = name.startswith(protected_member_prefix)
        is_private: bool = not is_protected and name.startswith(private_member_prefix)

        defining_class = find_defining_class(type(self), name)
        if caller_class is None:
            if is_protected:
                raise PermissionError(f"Access to protected member \"{name}\" of class \"{defining_class.__name__}\" not allowed.")
            if is_private:
                raise PermissionError(f"Access to private member \"{name}\" of class \"{defining_class.__name__}\" not allowed.")
            return setattribute_method(self, name, value)
    
        if is_private and caller_method_name not in dir(defining_class):
            raise PermissionError(f"Access to private member \"{name}\" not allowed.")
        if is_protected and not issubclass(caller_class, type(self)):
            raise PermissionError(f"Access to protected member \"{name}\" not allowed.")
        return setattribute_method(self, name, value)
    
    return getattribute_wrapper, setattr_wrapper
        


def strict_class(enabled: bool = True, private_member_prefix: str = "_", protected_member_prefix: str = "_p_"):
    def class_decorator(cls: type):
        if not enabled:
            return cls
        
        original_getattribute = cls.__getattribute__
        original_setattr = cls.__setattr__

        wrapped_getattribute, wrapped_setattr = _assume_self_strictness(
            original_getattribute, original_setattr, private_member_prefix, protected_member_prefix
        )

        cls.__getattribute__ = wrapped_getattribute
        cls.__setattr__ = wrapped_setattr

        return cls

    return class_decorator