$(function() {
    $("#search_button").click(function(){
        reset();
        $.post("search",
            {
                "disp_count": $('#disp_count').val(),
                "keyword": $('#keyword').val()
            },
            function(j_data){
                view(j_data);
            }
        );
    });
});

function reset() {
    $('svg').empty();
    $('#msg').empty();
}

function view(graph) {
    if(graph.error) {
        $('#msg').text(graph.error);
        exit();
    }

    var width = 800;
    var height = 600;

    var svg = d3.select("svg")
        .attr("width", width)
        .attr("height", height);

    var simulation = d3.forceSimulation()
        .force("link", d3.forceLink()
            .id(function(d) { return d.id; })
            .distance(function(d) { return d.distance * 150 + 50; }))
        .force("charge", d3.forceManyBody())
        .force("center", d3.forceCenter(width / 2, height / 2));


    var link = svg.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(graph.links)
        .enter().append("line");

    d3.selectAll("line")
        .attr("class", "link")

    var node = svg.append("g")
        .attr("class", "nodes")
        .selectAll("circle")
        .data(graph.nodes)
        .enter().append("circle")
            .attr("r", function(d){return d.size * 20 + 10})
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));

    var labels = svg.append("g")
        .selectAll("text")
        .data(graph.nodes)
        .enter()
        .append("a")
            .attr("xlink:href", function (d) { return "https://ja.wikipedia.org/wiki/" + d.id; })
            .attr("target", "_blank")
        .append("text")
            .text(function(d){return d.id;})
            .attr("class", "node-label");

    d3.selectAll("circle")
        .attr("class", "node");

    d3.select("circle")
        .attr("class", "node main");

    simulation
        .nodes(graph.nodes)
        .on("tick", ticked);

    simulation.force("link")
        .links(graph.links);

    function ticked() {
        link
            .attr("x1", function(d) { return d.source.x; })
            .attr("y1", function(d) { return d.source.y; })
            .attr("x2", function(d) { return d.target.x; })
            .attr("y2", function(d) { return d.target.y; });

        node
            .attr("cx", function(d) { return d.x; })
            .attr("cy", function(d) { return d.y; });

        labels
            .attr("x", function(d){return d.x;})
            .attr("y", function(d){return d.y;});
    }

    function dragstarted(d) {
        if (!d3.event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(d) {
        d.fx = d3.event.x;
        d.fy = d3.event.y;
    }

    function dragended(d) {
        if (!d3.event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}