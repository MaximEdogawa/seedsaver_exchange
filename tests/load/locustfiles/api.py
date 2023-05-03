from locust import HttpUser, between, task


class DefaultUser(HttpUser):

    # wait between requests from one user for between 1 and 5 seconds.
    wait_time = between(1, 5)

    @task
    def index(self):
        self.client.get("/")

