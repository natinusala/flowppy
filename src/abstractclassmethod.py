# -*- coding: utf-8 -*-

#"Hack" permettant d'avoir des méthodes abstraites et statiques
class abstractclassmethod(classmethod):
    __isabstractmethod__ = True;

    def __init__(self, callable):
        callable.__isabstractmethod__ = True;
        super(abstractclassmethod, self).__init__(callable);
