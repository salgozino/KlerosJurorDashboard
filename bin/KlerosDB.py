#!/usr/bin/python3

from sqlalchemy.sql.expression import func
import statistics
from datetime import datetime, timedelta
from bin import db


class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    option = db.Column(db.String(50))
    value = db.Column(db.String(50))

    @classmethod
    def get(cls, db_key):
        query = cls.query.filter(cls.option == db_key).first()
        if query == None: return None
        return query.value

    @classmethod
    def set(cls, db_key, db_val):
        query = cls.query.filter(cls.option == db_key)
        for item in query: db.session.delete(item)
        new_option = cls(option = db_key, value = db_val)
        db.session.add(new_option)
        db.session.commit()

class Court(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    address = db.Column(db.String(50))
    parent = db.Column(db.Integer, db.ForeignKey("court.id"), nullable=True)
    minStake = db.Column(db.Float)
    feeForJuror = db.Column(db.Float)
    voteStake = db.Column(db.Integer)
    

    def disputes(self, days=None):
        """
        Return the disputes in the previous days. If days is None, return all 
        the disputes in that Court

        Parameters
        ----------
        days : int, optional
            Number of days to count the disputes backwards.
            The default is None.

        Returns
        -------
        List
            List of all the Disputes

        """
        if days:
            filter_after = (datetime.now() - timedelta(days=days)).replace(hour=0, minute=0, second=0)
            return Dispute.query \
                .filter(Dispute.subcourtID == self.id, Dispute.timestamp >= filter_after ) \
                .order_by(Dispute.id.desc()).all()
        else:
            return Dispute.query.filter(Dispute.subcourtID == self.id).order_by(Dispute.id.desc()).all()

    def children_ids(self):
        children_ids = []
        children = Court.query.filter(Court.parent == self.id)
        for child in children:
            children_ids.append(child.id)
        return children_ids

    @staticmethod
    def getAllCourtChilds(courtID):
        childs = set(Court(id=courtID).children_ids())
        allChilds = []
        while childs:
            child = childs.pop()
            allChilds.append(child)
            childs.update(Court(id=child).children_ids())
        return allChilds


    @property
    def jurors(self):
        court_ids = [self.id]
        for c in self.children_ids():court_ids.append(c)
        juror_data = db.session.query(JurorStake.address, func.max(JurorStake.timestamp)) \
        .filter(JurorStake.subcourtID.in_(court_ids)) \
        .group_by(JurorStake.address).all()
        jurors = []
        for j in juror_data:
            jurors.append( Juror(j[0]) )
        return jurors

    def jurors_stakes_query(self):
        court_ids = [self.id]
        for c in self.children_ids():
            court_ids.append(c)
        return db.session.query(JurorStake.address, func.max(JurorStake.timestamp), JurorStake.setStake) \
        .filter(JurorStake.subcourtID.in_(court_ids)) \
        .group_by(JurorStake.address)
        
    def jurors_stakings(self):
        jurors_query = db.session.execute(
            "SELECT address, setStake, MAX(timestamp) as 'date' \
            FROM juror_stake \
            WHERE subcourtID = :court_id \
            GROUP BY address \
            ORDER BY setStake DESC", {'court_id': self.id})

        jurors = []
        for jq in jurors_query:
            juror = dict(jq.items())
            if juror['setStake'] != 0:
                jurors.append(juror)
        return jurors

    def juror_stats(self):
        amounts = []
        unique_jurors = []
        childCourts = self.getAllCourtChilds(self.id)
        childCourts.append(self.id)
        for courtID in childCourts:
            for juror in Court(id=courtID).jurors_stakings():
                amounts.append(juror['setStake'])
                if juror['address'] not in unique_jurors:
                    unique_jurors.append(juror['address']) 
        return {
            'length': len(amounts),
            'mean': statistics.mean(amounts),
            'median': statistics.median(amounts),
            'max': max(amounts),
            'total': sum(amounts),
            'uniqueJurors':len(unique_jurors),
        }
    

        


class Dispute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number_of_choices = db.Column(db.Integer)
    subcourtID = db.Column(db.Integer, db.ForeignKey("court.id"), nullable=False)
    status = db.Column(db.Integer)
    arbitrated = db.Column(db.String(50))
    current_ruling = db.Column(db.Integer)
    period = db.Column(db.Integer)
    last_period_change = db.Column(db.DateTime)
    ruled = db.Column(db.Boolean)
    creator = db.Column(db.String(50))
    txid = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime)
    blocknumber = db.Column(db.Integer)

    def rounds(self):
        return Round.query.filter_by(disputeID = self.id).all()

    @property
    def court(self):
        return Court.query.get(self.subcourtID)

    @property
    def period_name(self):
        period_name = {
            0 : "Evidence",
            1 : "Commit",
            2 : "Vote",
            3 : "Appeal",
            4 : "Execution",
        }
        return period_name[self.period]

    def delete_recursive(self):
        rounds = Round.query.filter(Round.disputeID == self.id)
        for r in rounds: r.delete_recursive()
        print("Deleting Dispute %s" % self.id)
        db.session.delete(self)
        db.session.commit()
     
    @property
    def openCases(self):
        openCases = self.query.filter(Dispute.ruled == 0).all()
        return len(openCases)
        
    @property
    def ruledCases(self):
        ruledCases = self.query.filter(Dispute.ruled == 1).all()
        return len(ruledCases)
        
    @staticmethod
    def mostActiveCourt(days=7):
        """
        Most active cour in the last days

        Parameters
        ----------
        days : int, optional
            DESCRIPTION. Last Days to filter. The default is 7.

        Returns
        -------
        Court object with the most active Court in the last days.

        """
        filter_after = datetime.today() - timedelta(days=days)
        
        disputes = Dispute.query.filter(Dispute.timestamp >= filter_after).all()
        counts = {}
        for dispute in disputes:
            try:
                counts[dispute.subcourtID] += 1
            except:
                counts[dispute.subcourtID] = 1
        mostActive = max(counts, key=counts.get)
        return {mostActive:counts[mostActive]}
            

class Round(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_num = db.Column(db.Integer)
    disputeID = db.Column(db.Integer, db.ForeignKey("dispute.id"), nullable=False)
    draws_in_round = db.Column(db.Integer)
    commits_in_round = db.Column(db.Integer)
    appeal_start = db.Column(db.Integer)
    appeal_end = db.Column(db.Integer)
    vote_lengths = db.Column(db.Integer)
    tokens_at_stake_per_juror = db.Column(db.Integer)
    total_fees_for_jurors = db.Column(db.Integer)
    votes_in_each_round = db.Column(db.Integer)
    repartitions_in_each_round = db.Column(db.Integer)
    penalties_in_each_round = db.Column(db.Integer)
    subcourtID = db.Column(db.Integer, db.ForeignKey("court.id"), nullable=False)

    def votes(self):
        return Vote.query.filter_by(round_id = self.id).all()

    def delete_recursive(self):
        votes = Vote.query.filter(Vote.round_id == self.id)
        for v in votes:
            print("Deleting vote %s" % v.id)
            db.session.delete(v)
        print("Deleting round %s" % self.id)
        db.session.delete(self)
        db.session.commit()

    @property
    def majority_reached(self):
        votes_cast = Vote.query.filter(Vote.round_id == self.id).filter(Vote.vote == 1).count()
        return votes_cast * 2 >= self.draws_in_round

    @property
    def winning_choice(self):
        votes = Vote.query.filter(Vote.round_id == self.id).count()
        votes_query = db.session.execute(
            "select choice,count(*) as num_votes from vote \
            where round_id = :round_id and vote=1 \
            group by choice order by num_votes desc", {'round_id': self.id}).first()
        return(votes_query[0])

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("round.id"), nullable=False)
    account = db.Column(db.String(50))
    commit = db.Column(db.Integer)
    choice = db.Column(db.Integer)
    vote = db.Column(db.Integer)
    date = db.Column(db.DateTime)

    @property
    def is_winner(self):
        round = Round.query.get(self.round_id)
        if not round.majority_reached: return False
        return self.choice == round.winning_choice

class Juror():
    def __init__(self, address):
        self.address = address.lower()

    @classmethod
    def list(cls):
        jurors_query = db.session.execute(
            "SELECT DISTINCT(vote.account), count(vote.id) from vote, round, dispute \
            WHERE vote.round_id = round.id \
            AND round.disputeID = dispute.id \
            GROUP BY vote.account"
        )
        jurors = []
        for jq in jurors_query:
            jurors.append({
                'address':jq[0],
                'votes': jq[1]
            })
        return jurors
    
    def stakedJurors():
        allStakes = db.session.execute(
            "SELECT MAX(id), address, subcourtID, setStake FROM juror_stake \
            group by subcourtID, address"
        )
        stakedJurors = {}
        for stake in allStakes:
            if stake.setStake > 0:
                if stake.address.lower() not in stakedJurors.keys():
                    stakedJurors[stake.address.lower()] = [{stake.subcourtID:stake.setStake}]
                else:
                    stakedJurors[stake.address.lower()].append({stake.subcourtID:stake.setStake})
            
        return stakedJurors


    def votes_in_court(self, court_id):
        votes_in_court = db.session.execute(
            "SELECT count(vote.id) from vote, round, dispute \
            WHERE vote.account = :address \
            AND vote.round_id = round.id \
            AND round.disputeID = dispute.id \
            AND dispute.subcourtID = :subcourtID",
            {'address': self.address, 'subcourtID' : court_id}
        )

        return votes_in_court.first()[0]

    @property
    def stakings(self):
        stakings_query = JurorStake.query.filter(JurorStake.address == self.address).order_by(JurorStake.timestamp.desc())
        stakings = []
        for staking in stakings_query:
            stakings.append(staking)
        return stakings
    
    @property
    def stakings_nonZero(self):
        stakings_query = JurorStake.query.filter(JurorStake.address == self.address).order_by(JurorStake.timestamp.desc())
        stakings = []
        for staking in stakings_query:
            if staking.setStake > 0:
                stakings.append(staking)
        return stakings
    
    @property
    def totalStaked(self):
        stakings_query = JurorStake.query.filter(JurorStake.address == self.address).order_by(JurorStake.timestamp.desc())
        stake = 0
        for staking in stakings_query:
            stake += staking.setStake
        return stake

    @property
    def current_stakings_per_court(self):
        stakings_query = db.session.execute(
            "SELECT MAX(id), subcourtID FROM juror_stake \
            WHERE address = :address \
            group by subcourtID", {'address': self.address }
        )
        stakings = {}
        for sq in stakings_query:
            stakings[sq[1]] = JurorStake.query.get(sq[0])
        return stakings

    def current_amount_in_court(self, court_id):
        stakings = self.current_stakings_per_court
        if court_id in stakings:
            court_only_stakings = stakings[court_id].setStake
        else:
            court_only_stakings = 0.0

        court_and_children = court_only_stakings

        court = Court.query.get(court_id)
        for child_id in court.children_ids():
            if child_id in stakings:
                court_and_children += stakings[child_id].setStake

        return {
            'court_only': court_only_stakings,
            'court_and_children': court_and_children
        }
    
    
    def retention():
        jurorsDrawn = Juror.list()
        jurorsDrawn = set(map(lambda x:x['address'].lower(),jurorsDrawn))
        activeJurors = Juror.stakedJurors()
        activeJurors = set(activeJurors.keys())
        jurorsRetained = activeJurors.intersection(jurorsDrawn)
        return len(jurorsRetained)

    def adoption(days=30):
        """
        Select the first stake for address in the past days.
        This is usefull to get the adoption
        """
        filter_after = (datetime.today() - timedelta(days=days)).replace(hour=0, minute=0, second=0)
        lastStakes = db.session.execute(
            "SELECT MIN(id), address, timestamp, setStake FROM juror_stake \
            WHERE setStake > 0 \
            group by address \
            order by timestamp desc").fetchall()
        newJuror = []
        for stake in lastStakes:
            if isinstance(stake[2],str):
                if datetime.strptime(stake[2], "%Y-%m-%d %H:%M:%S.%f") >= filter_after:
                    newJuror.append(stake)
            else:
                if stake[2] >= filter_after:
                    newJuror.append(stake)
        return newJuror
        


class JurorStake(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(50))
    subcourtID = db.Column(db.Integer, db.ForeignKey("court.id"), nullable=False)
    timestamp = db.Column(db.DateTime)
    setStake = db.Column(db.Float)
    txid = db.Column(db.String(100))
    blocknumber = db.Column(db.Integer)
    
    @staticmethod
    def last_blocknumber():
        return JurorStake.query.order_by(JurorStake.id.desc()).first().blocknumber


class Deposit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(50))
    cdate = db.Column(db.DateTime)
    amount = db.Column(db.Float)
    txid = db.Column(db.String(50))
    court_id = db.Column(db.Integer, db.ForeignKey("court.id"), nullable=False)
    token_contract = db.Column(db.String(50)) # FIXME

    @classmethod
    def total(cls):
        return cls.query.with_entities(func.sum(cls.amount)).all()[0][0]

class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dashboard = db.Column(db.Integer)
    map = db.Column(db.Integer)
    odds = db.Column(db.Integer)
    support = db.Column(db.Integer)
    unknown = db.Column(db.Integer)
    
    
    def __init__(self):
        try:
            currentVisitors = db.session.query(Visitor).get(1)
            self.dashboard = currentVisitors.dashboard
            self.map = currentVisitors.map
            self.odds = currentVisitors.odds
            self.support = currentVisitors.support
            self.unknown = currentVisitors.unknown
        except:
            self.dashboard = 0
            self.map = 0
            self.odds = 0
            self.support = 0
            self.unknown = 0
            db.session.add(self)
            db.session.commit()


    def __repr__(self):
        return f'Visitor({self.dashboard}, {self.map}, {self.odds}, {self.support}, {self.unknown})'
    
    def addVisit(self, page):
        currentVisitors = db.session.query(Visitor).get(1)
        if page == 'dashboard':
            currentVisitors.dashboard += 1
        elif page == 'odds':
            currentVisitors.odds += 1
        elif page == 'map':
            currentVisitors.map += 1
        elif page == 'support':
            currentVisitors.support += 1
        else:
            currentVisitors.unknown += 1
        db.session.commit()