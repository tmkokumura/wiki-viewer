/***********************
 * Ajaxイベント
 ***********************/
$(function() {
    /* リンクノードの表示ボタン押下時 */
    $("#btn_link").click(function(){
        reset();
        $.post("link",
            {
                "max-nodes": $('#max-nodes').val(),
                "keyword": $('#keyword-link').val()
            },
            function(j_data){
                display_link(j_data);
            }
        );
    });

    /* カテゴリツリーの表示ボタン押下時 */
    $("#btn_category").click(function(){
        reset();
        $.post("category",
            {
                "keyword": $('#keyword-category').val()
            },
            function(j_data){
                display_category(j_data);
            }
        );
    });
});

/***********************
 * 初期化関数
 ***********************/
function reset() {
    $('#canvas_link').empty();
    $('#canvas_category').empty();
    $('#msg_link').empty();
    $('#msg_category').empty();
}

/***************************
 * リンクノードの描画
 ***************************/
function display_link(graph) {
    if(graph.error) {
        $('#msg_link').text(graph.error);
        return;
    }

    var width = $('#canvas_link').width();
    var height = $('#canvas_link').height();

    var svg = d3.select("#canvas_link");

    var simulation = d3.forceSimulation()
        .force("link", d3.forceLink()
            .id(function(d) { return d.id; })
            .distance(function(d) { return d.distance * (height / 4) + (height / 10); }))
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

/***************************
 * カテゴリツリーの描画
 ***************************/
function display_category(data) {
    if(data.error) {
        $('#msg_category').text(graph.error);
        return;
    }

    var width = $('#canvas_category').width();
    var height = $('#canvas_category').height();

    var root = d3.hierarchy(data);

    var tree = d3.tree()
        .size([400,400]) // .size()でツリー全体のサイズを決める。

    tree(root);

    // 4. svg要素の配置
    var g = d3.select("#canvas_category").append("g").attr("transform", "translate(80,0)");
    var link = g.selectAll(".tree_link")
        .data(root.descendants().slice(1))
        .enter()
        .append("path")
        .attr("class", "tree_link")
        .attr("d", function(d) {
            return "M" + d.parent.y + "," + d.parent.x +
            "C" + ((d.parent.y + d.y)/2) + "," + d.parent.x +
            " " + ((d.parent.y + d.y)/2) + "," + d.x +
            " " + d.y + "," + d.x;
        });

    var node = g.selectAll(".tree_node")
        .data(root.descendants())
        .enter()
        .append("g")
        .attr("class", "tree_node")
        .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; })

    node.append("circle")
        .attr("r", 8)
        .attr("fill", "#999");

    node.append("a")
        .attr("xlink:href", function (d) { return "https://ja.wikipedia.org/wiki/Category:" + d.data.name; })
        .attr("target", "_blank")
        .attr("class", "tree_a")

    d3.selectAll(".tree_a")
        .append("text")
        .attr("dy", 3)
        .attr("x", function(d) { return d.children ? -12 : 12; })
        .style("text-anchor", function(d) { return d.children ? "end" : "start"; })
        .text(function(d) { return d.data.name; });
}