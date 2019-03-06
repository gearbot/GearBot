import {Component, h} from "preact";

import {AntiraidState, AntiraidBlock} from "./state";
import {AntiraidProps} from "./props";

export default class AntiRaidBuilder extends Component<AntiraidProps, AntiraidState> {
  
  blockTypes: [
    "duration",
    "joinCount",
    "in"
  ]

  constructor(props: AntiraidProps, state: AntiraidState) {
    super(props, state)
    this.setState({
      blockCount: 0,
      blockStates: []
    });
  }

  createBlock() {
    let newBlock: AntiraidBlock = {
      name: "TODO",
      displayText: "",
      description: "A block for building antiraid configs!",
      isBeingDragged: false,
      position: {x: 0, y: 0}
    };
    // TODO: Get user input for some of the strings and determine block type

    this.setState({
      blockCount: this.state.blockCount + 1,
      blockStates: this.state.blockStates.concat(newBlock)
    });
  }

  componentDidMount() {
    let entryBlock: AntiraidBlock = {
      name: "EntryBlock",
      displayText: "Entry",
      description: "The start of a AntiRaid config chain!",
      isBeingDragged: false,
      position: {x: 0, y: 0}
    }

    let endBlock: AntiraidBlock = {
      name: "EndBlock",
      displayText: "End",
      description: "The end of a AntiRaid config chain!",
      isBeingDragged: false,
      position: {x: 0, y: 0}
    }

    this.setState({ // Add our two marker blocks
      blockCount: 2,
      blockStates: [entryBlock, endBlock]
    })

    this.state.blockStates.forEach(block => {
      this.dragElement(document.getElementById("antiraidBlock-" + block.name))
      console.log(block) // At the moment its not actually rendering any blocks so this errors out
      console.log(document.getElementById("antiraidBlock-" + block.name))
    });
  }

  dragElement(elmnt) { //Thanks W3Schools
    var pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
    if (document.getElementById(elmnt.id + "header")) {
      /* if present, the header is where you move the DIV from:*/
      document.getElementById(elmnt.id + "header").onmousedown = dragMouseDown;
    } else {
      /* otherwise, move the DIV from anywhere inside the DIV:*/
      elmnt.onmousedown = dragMouseDown;
    }
  
    function dragMouseDown(e) {
      e = e || window.event;
      e.preventDefault();
      // get the mouse cursor position at startup:
      pos3 = e.clientX;
      pos4 = e.clientY;
      document.onmouseup = closeDragElement;
      // call a function whenever the cursor moves:
      document.onmousemove = elementDrag;
    }
  
    function elementDrag(e) {
      e = e || window.event;
      e.preventDefault();
      // calculate the new cursor position:
      pos1 = pos3 - e.clientX;
      pos2 = pos4 - e.clientY;
      pos3 = e.clientX;
      pos4 = e.clientY;
      // set the element's new position:
      elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
      elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
    }
  
    function closeDragElement() {
      /* stop moving when mouse button is released:*/
      document.onmouseup = null;
      document.onmousemove = null;
    }
  }

	render() {
    return (
      <div class="antiraidBuilder">
        <button id="createRaidBlockButton" onClick={this.createBlock}>Create Block</button>
        {
          this.state.blockStates.forEach(block => { // These don't render at the moment
            <div class="antiraidBlock" id={"antiraidBlock-" + block.name}>{block.displayText}</div>
          })
        }
      </div>
    );
	}
}