import networkx as nx
from operator import itemgetter

from structures import mdl_encoding


def modified_slash_burn(current_gcc, hubset_k, gcc_num_nodes_criterion,
                        total_num_nodes, top_k_queue, iteration):
    gccs = []

    print "Finding k hubset", current_gcc.number_of_nodes(), current_gcc.number_of_edges()
    # 1
    # get a sorted list of (node, degree) in decreasing order
    k_hubset_nd = sorted(current_gcc.degree_iter(), key=itemgetter(1), reverse=True)
    # get the node index for the k highest degree vertex
    k_hubset = [i[0] for i in k_hubset_nd[0:hubset_k]]

    # consider subgraphs (stars) consisting of centrality nodes from the k hubset we are about to slash
    for node in k_hubset:
        hubset_subgraph = current_gcc.neighbors(node)
        hubset_subgraph.append(node)
        structure = mdl_encoding(current_gcc.subgraph(hubset_subgraph), total_num_nodes)
        try:
            top_k_queue.put(structure)
        except Exception as e:
            print "Manager was shut down so shouldn't be adding subgraphs", e
            break

    # remove the k hubset from G, so now we have G' (slash!)
    current_gcc.remove_nodes_from(k_hubset)

    print "Finding remaining subgraphs after having removed k hubset"
    # 2
    # get all the subgraphs after removing the k hubset
    subgraphs = nx.connected_component_subgraphs(current_gcc, copy=False)

    print "Iterating over remaining subgraphs and spinning off labeling if less than certain size"
    # iterate over the remaining subgraphs we are "burning"
    for subgraph in subgraphs:
        if subgraph.number_of_nodes() <= gcc_num_nodes_criterion:
            structure = mdl_encoding(subgraph, total_num_nodes)
            try:
                top_k_queue.put(structure)
            except Exception as e:
                print "Manager was shut down so shouldn't be adding subgraphs", e
                break
        else:
            # append the subgraph to GCCs queue
            gccs.append(subgraph)

    return iteration, gccs


def k_hop_egonets(current_egonet, min_egonet_size, egonet_num_nodes_criterion, hop_k,
                  total_num_nodes, top_k_queue, iteration):
    egonets = []

    # 1
    # get a sorted list of (node, degree) in decreasing order
    node_degrees = sorted(current_egonet.degree_iter(), key=itemgetter(1), reverse=True)

    for node, degree in node_degrees:
        # if the node was removed as part of a previous egonet don't consider it any more
        if not nx.degree(current_egonet, [node]):
            continue
        elif degree > min_egonet_size:
            # iteratively build the k hop neighbors for the current node in consideration
            k_hop_neighbors = set()
            k_hop_neighbors.add(node)
            neighbors = [node]
            for hop in range(hop_k):
                next_neighbors = set()
                for n in neighbors:
                    for nn in current_egonet.neighbors(n):
                        if nn not in k_hop_neighbors:
                            next_neighbors.add(nn)
                k_hop_neighbors = k_hop_neighbors.union(next_neighbors)
                neighbors = next_neighbors

            # construct a subgraph from the k hop neighbors and induced edges
            subgraph = current_egonet.subgraph(k_hop_neighbors)
            # and remove the k hop neigbors from the current egonet in consideration
            current_egonet.remove_nodes_from(k_hop_neighbors)
            if subgraph.number_of_nodes() <= egonet_num_nodes_criterion:
                structure = mdl_encoding(subgraph, total_num_nodes)
                try:
                    top_k_queue.put(structure)
                except Exception as e:
                    print "Manager was shut down so shouldn't be adding subgraphs", e
                    break
            else:
                egonets.append(subgraph)
        else:
            break

    return iteration, egonets

