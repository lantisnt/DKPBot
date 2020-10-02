from essentialdkp_bot import EssentialDKPBot
from display_templates import SinglePlayerProfile

class MonolithDKPBot(EssentialDKPBot):

    def _configure(self):
        super()._configure()
        # Data outputs
        self._single_player_profile_builder = SinglePlayerProfile("Monolith DKP Profile")
