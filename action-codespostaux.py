#!/usr/bin/env python3
import textwrap

from hermes_python.hermes import Hermes
from hermes_python.ontology import MqttOptions
import requests

import snips_common


OVERPASS_URL = "http://overpass-api.de/api/interpreter"


class NotFound(Exception):
    pass


class ActionCodesPostaux(snips_common.ActionWrapper):
    reactions = {NotFound: "Désolée, je n'ai rien trouvé sur la ville de {}."}

    def action(self):
        city = self.intent_message.slots.ville.first().value

        # Should be accurate enough without relying on Nominatim
        query = textwrap.dedent(  # TODO country from conf
            """
                [out:json];
                area["ISO3166-1"="FR"][admin_level=2];
                (
                    rel["name:fr"="%s"];
                );
                out tags;
            """
            % (city,)
        )
        response = requests.get(OVERPASS_URL, params={'data': query})
        response.raise_for_status()

        elements = response.json()['elements']
        if not elements:
            raise NotFound(city)

        tags = elements[0]['tags']
        found_city = tags.get('name:fr', city)

        try:
            postcodes = tags['addr:postcode'].split(";")
        except KeyError:
            raise NotFound(found_city)

        if len(postcodes) > 1:
            self.end_session(
                "Il y a quatre codes postaux pour la ville de", found_city, *postcodes
            )
        else:
            self.end_session("Le code postal de", found_city, "est", postcodes[0])


if __name__ == "__main__":
    mqtt_opts = MqttOptions()

    with Hermes(mqtt_options=mqtt_opts) as h:
        h.subscribe_intent("roozeec:codepostal", ActionCodesPostaux.callback).start()
