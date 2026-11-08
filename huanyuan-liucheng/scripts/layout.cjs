// Copyright (c) 2026 Gin. All rights reserved. See LICENSE in the skill root.
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const dagre = vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../vendor/dagre-3.1.3.js'),'utf8') + '\n;dagre', {structuredClone});
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const graph = new dagre.graphlib.Graph({multigraph:true});
graph.setGraph({rankdir:'TB',align:'UR',ranksep:64,nodesep:70,edgesep:36,marginx:36,marginy:30,acyclicer:'greedy'});
graph.setDefaultEdgeLabel(()=>({}));
for (const node of input.nodes) graph.setNode(node.id,node);
for (const edge of input.edges) graph.setEdge(edge.source,edge.target,edge,edge.id);
dagre.layout(graph);
// Mirror the right-aligned graph: the main continuation reads on the left.
const fullWidth = graph.graph().width;
for (const id of graph.nodes()) graph.node(id).x = fullWidth - graph.node(id).x;
for (const id of graph.edges()) {
  const edge = graph.edge(id);
  if (Number.isFinite(edge.x)) edge.x = fullWidth - edge.x;
  for (const point of edge.points) point.x = fullWidth - point.x;
}
process.stdout.write(JSON.stringify({
  width:graph.graph().width,height:graph.graph().height,
  nodes:graph.nodes().map(id=>graph.node(id)),
  edges:graph.edges().map(edge=>graph.edge(edge))
}));
