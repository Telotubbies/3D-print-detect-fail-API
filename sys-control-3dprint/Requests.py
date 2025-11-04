import requests

# API_KEY = "8AvRbX9eTN9YZyzesD6CQJG9hJDRnvJzz8J8ZaXmrQE"
# HOST_URL = "http://192.168.214.181:5002"

# See https://docs.octoprint.org/en/master/api/general.html#authorization for
# where to get this value

# UI_API_KEY = "j00_vQA6U_kk0SEQzcSo_4fXzJZIZikFaX4FDKIWRkw"
UI_API_KEY = "gl3ye-kMFFW6eRuDp98Y2cyME19SXApyId_Y8QuL_b0"


# Change this to match your printer
HOST_URL = "https://ender1.serveo.net"


# headers = {"X-Api-Key": API_KEY, "Content-Type": "application/json"}


def set_active(active):
    return requests.post(
        f"{HOST_URL}/plugin/continuousprint/set_active",
        headers={"X-Api-Key": UI_API_KEY},
        data={"active": active},
    ).json()


def add_set(path, sd=False, count=1, jobName="Job", jobDraft=True):
    return requests.post(
        f"{HOST_URL}/plugin/continuousprint/set/add",
        headers={"X-Api-Key": UI_API_KEY},
        data=dict(
            path=path,
            sd=sd,
            count=count,
            jobName=jobName,
            jobDraft=jobDraft,
        ),
    ).json()


def get_state():
    return requests.get(
        f"{HOST_URL}/plugin/continuousprint/state/get",
        headers={"X-Api-Key": UI_API_KEY},
    ).json()


if __name__ == "__main__":
    # print("👉 Start managing queue")
    # print(set_active(True))

    # print("👉 Stop managing queue")
    # print(set_active(False))

    print("👉 Check state")
    print(get_state())
