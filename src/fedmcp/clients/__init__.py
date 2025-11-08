"""Client modules for accessing Canadian parliamentary and legal data sources."""

from .openparliament import OpenParliamentClient
from .ourcommons import OurCommonsHansardClient, HansardSitting, HansardSection, HansardSpeech
from .legisinfo import LegisInfoClient
from .canlii import CanLIIClient
from .represent import RepresentClient
from .expenditure import MPExpenditureClient, MPExpenditure
from .house_officers import HouseOfficersClient, HouseOfficerExpenditure
from .petitions import PetitionsClient, Petition, PetitionSponsor
from .lobbying import LobbyingRegistryClient, LobbyingRegistration, LobbyingCommunication
from .federal_contracts import FederalContractsClient, FederalContract
from .grants_contributions import GrantsContributionsClient, GrantContribution
from .political_contributions import PoliticalContributionsClient, PoliticalContribution
from .departmental_expenses import DepartmentalExpensesClient, DepartmentalTravel, DepartmentalHospitality

__all__ = [
    "OpenParliamentClient",
    "OurCommonsHansardClient",
    "HansardSitting",
    "HansardSection",
    "HansardSpeech",
    "LegisInfoClient",
    "CanLIIClient",
    "RepresentClient",
    "MPExpenditureClient",
    "MPExpenditure",
    "HouseOfficersClient",
    "HouseOfficerExpenditure",
    "PetitionsClient",
    "Petition",
    "PetitionSponsor",
    "LobbyingRegistryClient",
    "LobbyingRegistration",
    "LobbyingCommunication",
    "FederalContractsClient",
    "FederalContract",
    "GrantsContributionsClient",
    "GrantContribution",
    "PoliticalContributionsClient",
    "PoliticalContribution",
    "DepartmentalExpensesClient",
    "DepartmentalTravel",
    "DepartmentalHospitality",
]
