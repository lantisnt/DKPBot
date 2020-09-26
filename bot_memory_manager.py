import os, collections, time

import dkp_bot

class Manager:

    __limit = 75
    __tracker = None
    __bots = None
    __save_fn = None
    __restore_fn = None
    def __init__(self, limit, bots, save_fn, restore_fn):
        if isinstance(limit, int):
            self.__limit = limit
        
        # Bots handled by core
        self.__bots = bots

        # Tracker
        self.__tracker = collections.OrderedDict()

        # Storage callbacks
        self.__save_fn = save_fn
        self.__restore_fn = restore_fn

    ## Remove oldest used bot and push newer one
    def __swap(self, server_id: int):
        item = self.__tracker.popitem(False)
        self.__save(item[0])
        self.__restore(server_id)
        self.__add(server_id)

    ## Update one bot status
    def __update(self, server_id: int):
        self.__remove(server_id)
        self.__add(server_id)

    ## Add bot to tracking
    def __add(self, server_id: int):
        self.__tracker[server_id] = True

    ## Remove bot from tracking
    def __remove(self, server_id: int):
        del self.__tracker[server_id]

    ## Save bot database
    def __save(self, server_id: int):
        ## handle the data and save it through the api
        print("Save {0}".format(server_id))
        data = self.__bots[server_id].DatabaseGet()
        self.__save_fn(server_id, data)
        self.__bots[server_id].DatabaseFree()

    ## Restore bot database
    def __restore(self, server_id: int):
        print("Restore {0}".format(server_id))
        data = self.__restore_fn(server_id)
        self.__bots[server_id].DatabaseSet(data)
        ## restore the data it through the api and handle it

    ## Main Handler
    def Handle(self, server_id: int) -> None:
        # If memory storage is full handle swap
        print("Memory {0} tracker elements.".format(len(self.__tracker)))
        if len(self.__tracker) >= self.__limit:
            self.__swap(server_id)
        # Else if we have still spot check if we are tracking the requester
        elif server_id in self.__tracker.keys():
            self.__update(server_id)
        # Else if we have still spot and we are not tracking requester we handle the adding
        else:
            self.__add(server_id)
        
