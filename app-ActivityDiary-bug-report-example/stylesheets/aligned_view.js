let app = new Vue({
    el: '#app',
    data: {
        event_edge_seed_dynamic_list: [],
    },
    methods: {
        img: (src) => {
            if (!src) return '';
            return '<img src="' + src + '"  alt=""/>'
        }
    },
    mounted: function () {
        // identify delta in seed test
        console.assert(checking_result['unmatched_views_of_seed_test']);
        let seed_delta = checking_result['unmatched_views_of_seed_test'].find((e) => {
            return e['annotated_utg_file'] === utg_file_name;
        });
        console.assert(seed_delta);
        let delta_seed_from_state = seed_delta['from_state_id'],
            delta_seed_to_state = seed_delta['to_state_id'];

        // normalize
        let preprocessed = utg['edges'].reduce((prev, edge) => {
            let type = edge['from'].slice(-3);
            console.assert(type === edge['to'].slice(-3));

            edge['events'].forEach((event) => {
                prev[type].push([event['event_id'], edge, event])
            });

            return prev
        }, {
            '[s]': [],
            '[m]': [],
            '[d]': [],
        });

        // cleanup nop
        for (let key in preprocessed) {
            preprocessed[key].sort((a, b) => parseInt(a[0]) - parseInt(b[0]));
            for (let i = preprocessed[key].length - 1; i >= 0; i--) {
                let e = preprocessed[key][i];
                if (e[2]['event_type'] === 'nop') {
                    console.assert(i > 0);
                    preprocessed[key][i - 1][1] = {...preprocessed[key][i - 1][1], to: preprocessed[key][i][1]['to']}
                    preprocessed[key].splice(i, 1);
                }
            }
        }

        let mutant_length = preprocessed['[m]'].length,
            mutant_insert_count = preprocessed['[m]'].filter((v) => v[2]['is_inserted_event']).length,
            mutant_insert_position = utg['insert_start_position'];

        let edges = preprocessed;
        console.log(mutant_insert_count, mutant_insert_position)
        // insert null into seed edges for corresponding mutant edges
        for (let index = 1; index <= edges['[s]'].length; index++) {
            if (mutant_insert_position === 0) {
                for (let _ = 0; _ < mutant_insert_count; _++) {
                    edges['[s]'].splice(0, 0, null);
                }
                break;
            }
            if (index === edges['[s]'].length) {
                for (let _ = 0; _ < mutant_insert_count; _++) {
                    edges['[s]'].splice(index, 0, null);
                }
                break;
            }
            console.log(edges['[s]'][index][0]-1, edges['[s]'][index-1][0]-1)
            if (
                    edges['[s]'][index][0] > mutant_insert_position
                    && edges['[s]'][index - 1][0] <= mutant_insert_position
                ) {
                for (let _ = 0; _ < mutant_insert_count; _++) {
                    edges['[s]'].splice(index, 0, null);
                }
                break;
            }
        }
        console.log(edges['[s]'])

        console.assert(preprocessed['[s]'].length === mutant_length);

        let seed_dynamic_edges = edges['[s]'].map((e, i) => {
            let dynamic_e = edges['[d]'][i] === undefined ? null : edges['[d]'][i];
            if (e !== null && dynamic_e !== null) {
                console.assert(e['color'] === edges['[d]'][i]['color'])
            }
            return [e, dynamic_e];
        });

        let seed_is_delta = false;
        this.event_edge_seed_dynamic_list = seed_dynamic_edges.reduce((prev, e, i, a) => {
            let seed_edge = e[0], dynamic_edge = e[1];

            let first = i === 0;
            if (first) {
                // if first event in seed is inserted,
                // we still want align the initial state
                // find the real first state and place the first state at first line
                for (let seed_find_anchor = 0; seed_find_anchor < seed_dynamic_edges.length; seed_find_anchor++) {
                    if (seed_dynamic_edges[seed_find_anchor][0] !== null) {
                        prev[0][0] = '';
                        prev[0][1] = this.img(state_of_edge(seed_dynamic_edges[seed_find_anchor][0], false));
                        break;
                    }
                }
                prev[0][2] = '';
                prev[0][3] = this.img(state_of_edge(dynamic_edge, false));
            }

            prev.push([
                this.img(event_of_edge(seed_edge)) + event_type_of_edge(seed_edge), this.img(state_of_edge(seed_edge)),
                this.img(event_of_edge(dynamic_edge)) + event_type_of_edge(dynamic_edge), this.img(state_of_edge(dynamic_edge)),
                {},
            ]);

            if (seed_edge !== null) {
                if (!seed_is_delta && seed_edge[0] === delta_seed_from_state + 1) {
                    for (let j = i; j >= 0; j--) {
                        if (j >= 0 && prev[j][1] === "") continue;
                        prev[j][4]['seed-delta'] = true;
                        break;
                    }
                    seed_is_delta = true;
                }
                if (seed_is_delta) {
                    if (seed_edge[0] === delta_seed_to_state) {
                        prev[i + 1][4]['seed-delta'] = true;
                        seed_is_delta = false;
                    } else if (seed_edge[0] > delta_seed_to_state) {
                        for (let j = i - 1; j >= 0; j--) {
                            if (seed_dynamic_edges[j][0] === null) continue;
                            if (seed_dynamic_edges[j][0][0] <= delta_seed_to_state) {
                                prev[j + 1][4]['seed-delta'] = true;
                                seed_is_delta = false;
                            }
                            break;
                        }
                    } else if (i + 1 === a.length) {
                        // last line
                        prev[i + 1][4]['seed-delta'] = true;
                        seed_is_delta = false;
                    }
                }
            }

            return prev;
        }, [
            ['empty event', 'first state', 'empty event', 'first state', {}],
        ]);
    }
});

// e := [event_id, edge, event]

function event_type_of_edge(e) {
    if (e === null) return '';
    let str = e[2]['event_str'];
    if (!(typeof str === 'string' || str instanceof String)) {
        str = str[0];
    }
    return '<p>' + e[2]['event_id'] + ': ' + str + '</p>'
}

function event_of_edge(e) {
    if (e === null) return '';
    return e[2]['view_images'][0];
}

function state_of_edge(e, is_second = true) {
    if (e === null) return '';
    let s = is_second ? e[1].to : e[1].from;
    let r = utg['nodes'].find((e) => e['id'] === s);
    if (r === undefined) {
        console.warn(s + ' state not found');
        return '';
    }
    return r['image'];
}