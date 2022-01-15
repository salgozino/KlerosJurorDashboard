from flask_login import UserMixin
from app.modules.subgraph import KBSubscriptionsSubgraph


class User(UserMixin):
    """
    Flask-login user class.
    """

    def __init__(self, id=None):
        self.id = str(id)
        self._is_authenticated = id is not None
        self._is_active = True
        self._is_anonymous = id is None
        self._is_donor = KBSubscriptionsSubgraph().isDonor(id)
        self._total_donated = \
            KBSubscriptionsSubgraph().getDonorTotalDonated(id)

    @property
    def is_authenticated(self):
        return self._is_authenticated

    @is_authenticated.setter
    def is_authenticated(self, val):
        self._is_authenticated = val

    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, val):
        self._is_active = val

    @property
    def is_anonymous(self):
        return self._is_anonymous

    @is_anonymous.setter
    def is_anonymous(self, val):
        self._is_anonymous = val

    def get_id(self):
        return self.id

    @property
    def is_donor(self):
        return self._is_donor

    @is_donor.setter
    def is_donor(self, val):
        self._is_donor = val

    @property
    def total_donated(self):
        return self._total_donated

    @total_donated.setter
    def total_donated(self, val):
        self._total_donated = val
