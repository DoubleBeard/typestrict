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


def get_wrappers(
        getattribute_method: MethodType,
        setattribute_method: MethodType,
        private_member_prefix: str,
        protected_member_prefix: str,
        enforce_private_variables: bool,
        enforce_protected_variables: bool,
        enforce_variable_decleration: bool):
    
    def getattribute_wrapper(self, name: str) -> Any:
        # Dunder methods should run as usual
        if name.startswith("__") and name.endswith("__"):
            return getattribute_method(self, name)

        # Check if variable is public, private or protected
        is_protected: bool = name.startswith(protected_member_prefix)
        is_private: bool = not is_protected and name.startswith(private_member_prefix)

        is_protected = is_protected and enforce_protected_variables
        is_private = is_private and enforce_private_variables

        caller_class, caller_method_name = get_caller()
        defining_class = find_defining_class(type(self), name)

        # Variable was not called by a method
        if caller_class is None:
            if is_protected:
                raise PermissionError(f"Access to protected member \"{name}\" of class \"{defining_class.__name__}\" not allowed.")
            if is_private:
                raise PermissionError(f"Access to private member \"{name}\" of class \"{defining_class.__name__}\" not allowed.")
            return getattribute_method(self, name)

        # Variable was called by a method, check if the class has access permissions to it
        if is_private and caller_method_name not in dir(defining_class):
            raise PermissionError(f"Access to private member \"{name}\" of class \"{defining_class.__name__}\" not allowed.")
        if is_protected and not issubclass(caller_class, type(self)):
            raise PermissionError(f"Access to protected member \"{name}\" of class \"{defining_class.__name__}\" not allowed.")
        return getattribute_method(self, name)

    def setattr_wrapper(self, name: str, value: Any) -> Any:
        # Dunder methods should run as usual
        if name.startswith("__") and name.endswith("__"):
            return setattribute_method(self, name, value)
    
        # Prevent setting values for undeclared variables
        if enforce_variable_decleration:
            valid_attrs = {attr for cls in self.__class__.mro() for attr in cls.__dict__}
            valid_annotations = {attr for cls in self.__class__.mro() for attr in getattr(cls, '__annotations__', {})}
            
            if name not in valid_attrs and name not in valid_annotations:
                raise AttributeError(f"Attribute '{name}' is undeclared in class '{self.__class__.__name__}'.")
        
        # Check if variable is public, private or protected
        is_protected: bool = name.startswith(protected_member_prefix)
        is_private: bool = not is_protected and name.startswith(private_member_prefix)

        is_protected = is_protected and enforce_protected_variables
        is_private = is_private and enforce_private_variables

        caller_class, caller_method_name = get_caller()
        defining_class = find_defining_class(type(self), name)

        # Variable was not called by a method
        if caller_class is None:
            if is_protected:
                raise PermissionError(f"Access to protected member \"{name}\" of class \"{defining_class.__name__}\" not allowed.")
            if is_private:
                raise PermissionError(f"Access to private member \"{name}\" of class \"{defining_class.__name__}\" not allowed.")
            return setattribute_method(self, name, value)

        # Variable was called by a method, check if the class has access permissions to it
        if is_private and caller_method_name not in dir(defining_class):
            raise PermissionError(f"Access to private member \"{name}\" not allowed.")
        if is_protected and not issubclass(caller_class, type(self)):
            raise PermissionError(f"Access to protected member \"{name}\" not allowed.")
        return setattribute_method(self, name, value)
    
    return getattribute_wrapper, setattr_wrapper
        


def strict_class(
        enabled: bool = True,
        private_member_prefix: str = "_",
        protected_member_prefix: str = "_p_",
        *,
        enforce_private_variables: bool = True,
        enforce_protected_variables: bool = True,
        enforce_variable_decleration: bool = True):
    
    def class_decorator(cls: type):
        if not enabled:
            return cls
        
        original_getattribute = cls.__getattribute__
        original_setattr = cls.__setattr__

        wrapped_getattribute, wrapped_setattr = get_wrappers(
            original_getattribute,
            original_setattr,
            private_member_prefix,
            protected_member_prefix,
            enforce_private_variables,
            enforce_protected_variables,
            enforce_variable_decleration
        )

        cls.__getattribute__ = wrapped_getattribute
        cls.__setattr__ = wrapped_setattr

        return cls

    return class_decorator