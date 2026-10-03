from candor import links


def test_links_are_symmetric_and_typed(corpus):
    graph = links.build(corpus)
    kinds = {links.EMAIL_THREAD, links.DICTATION_SENT, links.SLACK_THREAD, links.MEETING_EVENT}
    for a, partners in graph.items():
        for b, kind in partners.items():
            assert kind in kinds
            assert graph[b][a] == kind


def test_dictation_links_point_forward_to_the_owners_own_messages(corpus):
    graph = links.build(corpus)
    by_id = {u.id: u for u in corpus.units}
    pairs = [(a, b) for a, ps in graph.items() for b, k in ps.items()
             if k == links.DICTATION_SENT and by_id[a].source == "dictation"]
    assert pairs, "expected at least one dictation that was sent"
    for d, sent in pairs:
        assert by_id[sent].speaker == corpus.owner
        assert by_id[d].time <= by_id[sent].time <= by_id[d].time + links.DICTATION_WINDOW


def test_discarded_dictations_never_link(corpus):
    graph = links.build(corpus)
    for u in corpus.units:
        if u.source == "dictation" and u.meta["delivery_state"] == "discarded":
            assert not any(k == links.DICTATION_SENT for k in graph.get(u.id, {}).values()), u.id
