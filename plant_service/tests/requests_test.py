import requests


def test():
    #Is it so that im denying even myself from sending myself requests?
    # basically request going through me?
    r = requests.get('http://localhost/api/plants:9999')
    print(r)


test()
