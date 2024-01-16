from .._utils import DefaultFuncs
import time,json,random
def create_new_group(default_funcs: DefaultFuncs, ctx: dict):
        def create(participants:list,groupTitle:str):
            if len(participants)<2:
                  raise ValueError('error: "createNewGroup: participantIDs should have at least 2 IDs."')
            pids=[]
            for ids in participants:
                  pids.append({"fbid":ids})
            pids.append({"fbid":ctx["user_id"]})
            print(pids)
            form = {
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "MessengerGroupCreateMutation",
            "av": ctx["user_id"],
            "doc_id": "577041672419534",
            "variables": json.dumps({
                "input": {
                "entry_point": "jewel_new_group",
                "actor_id": ctx["user_id"],
                "participants": pids,
                "client_mutation_id": str(round(random.random() * 1024)),
                "thread_settings": {
                    "name": groupTitle,
                    "joinable_mode": "PRIVATE",
                    "thread_image_fbid": None
                }
                }
            })
            }
            default_funcs.post_with_defaults("https://www.facebook.com/api/graphql/",form,ctx).text
        return create