const plotSection = document.getElementById("plot-section");

import {PlotCreator} from './SanKEY_script.js'

const createSankey = (nodes, links, options) => {
    // plotSection.innerHTML = ""; // clear the plot section first
    new PlotCreator(
        plotSection, // container in the dom
        nodes,
        links,
        plotSection.clientWidth, // plot width
        plotSection.clientHeight, // plot height
        0, // first column to show
        5, // last column to show (e.g. 0, 4 shows columns 0-3)

        // further options
        // combination of "options" param and options defined here
        Object.assign(options, {
            on_link_hover_function: (link_info,link_data_reference,link_element,event) => {
                return `${link_info["from_label"]}<br>${Math.round(link_info["value"])} TJ<br>${link_info["to_label"]}`
            }
        })
    )
}

// to let us use the function outside of this module
window.createSankey = createSankey;

/* OLD Code

// to hold the div in which is the plot
var plotSection;

// zooming variables
var plotZoom;

// panning variables
var plotPanX, plotPanY, dragging, originX, originY;

const updatePlot = () => {
    // devide by plotZoom so that the image doesn't move relatively faster the more zoomed a user is
    plotSection.style.transform = "scale(" + plotZoom + ") translate(" + plotPanX / plotZoom + "px," + plotPanY / plotZoom + "px)";
}

const resetPlot = () => {
    plotSection.style.transform = "scale(1) translate(0px,0px)";
    plotZoom = 1;
    plotPanX = plotPanY = 0;
    dragging = false;
}

const initPlotUtils = () => {
    plotSection = document.querySelector("div div.plotly-graph-div");
    resetPlot();

    // zooming
    plotSection.onwheel = (event) => {
        event.preventDefault();

        // if scrolling wheel up, increase zoom
        if (event.deltaY < 0)
            plotZoom *= 1.1;

        // if scrolling wheel down, decrease zoom
        else
            plotZoom /= 1.1;

        // TODO: zoom into where the user's mouse points
        // plotSection.style.transformOrigin = event.clientX / plotZoom + "px " + event.clientY / plotZoom + "px";
        updatePlot();
    }

    // panning

    // get mouse down to start panning
    plotSection.onmousedown = (event) => {

        // if middle mouse button was clicked
        if (event.which == 2 || event.button == 4) {
            event.preventDefault()
            dragging = true;
            originX = event.clientX - plotPanX;
            originY = event.clientY - plotPanY;
        }
    }

    // get mouse up to stop panning
    plotSection.onmouseup = () => {
        dragging = false;
    }

    // get mouse movement to pan
    plotSection.onmousemove = (event) => {
        // only pan if holding mouse button down
        if (dragging) {
            plotPanX = event.clientX - originX;
            plotPanY = event.clientY - originY;
            updatePlot();
        }
    }

}

// listener to initialize this script when htmx loads in a new plot
// htmx.on("htmx:afterSwap", (event) => {
//     if (event.detail.target.id == "plot-section")
//          initPlotUtils();
// });

end OLD Code */