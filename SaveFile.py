import os.path
import pickle
import pprint
import traceback
import aiofiles

class SaveFile():
    def __init__(self,name):
        self.name=f'{name}/'

    def get(self,name,default=None):
        name = self.name + name+'.bin'
        try:
            if os.path.exists(name):
                print('loading ' + name)
                with open(name, 'rb') as f:
                    value= pickle.load(f,fix_imports=True)
                    #pprint.pprint(value)
                    return value
            else:
                if default is not None:
                    print('craeting default ' + name)
                    value = default
                    with open(name, 'wb') as f:
                        pickle.dump(value, f)
                value=default
        except:
            traceback.print_exc()
            print("Can't load "+name)
            raise ValueError()
            if default is not None:
                print('craeting default ' + name)
                value = default
                with open(name, 'wb') as f:
                    pickle.dump(value, f)
            value = default

        return value
    async def async_get(self,name,default=None):
        name = self.name + name+'.bin'
        try:
            if os.path.exists(name):
                #print('loading ' + name)
                async with aiofiles.open(name, 'rb') as f:
                    content=await f.read()
                    value= pickle.loads(content,fix_imports=True)
                    #pprint.pprint(value)
                    return value
            else:
                if default is not None:
                    print('creating default ' + name)
                    value = default
                    async with aiofiles.open(name, 'wb') as f:
                        value=pickle.dumps(value)
                        await f.write(value)
                value=default
        except:
            traceback.print_exc()
            print("Can't load "+name)
            if default is not None:
                print('craeting default ' + name)
                value = default
                async with aiofiles.open(name, 'wb') as f:
                    await f.write(pickle.dumps(value))
            value = default

        return value
    def exists(self,stri):
        path = self.name + stri + '.bin'
        return os.path.exists(path)

    def set(self,name,value):
        name = self.name + name + '.bin'
        with open(name, 'wb') as f:
            pickle.dump(value, f)
    async def async_set(self,name,value):
        name = self.name + name + '.bin'
        async with aiofiles.open(name, 'wb') as f:
            await f.write(pickle.dumps(value))
    def save(self):
        pass





