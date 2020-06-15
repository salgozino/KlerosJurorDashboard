from Kleros import KlerosLiquid, StakesKleros

KlerosLiquid().updateDB()
StakesKleros().calculateStakedInCourts()
StakesKleros().calculateHistoricStakesInCourts()
StakesKleros().calculateHistoricJurorsInCourts()