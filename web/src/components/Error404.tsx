import {Component, h} from "preact";

export default class Error404 extends Component<{}, {}> {

	render() {
		return (
			<div class="error404">
				<h1 id="warning">WHOOPS</h1>
				<img style="float: left;" id="leftgear" className="gear404 gear" src="/assets/gear.svg"/>
				<img style="float: right;" id="rightgear" className="gear404 gear" src="/assets/gear.svg"/>
				<h1 id="errorcode">404: GEAR NOT FOUND</h1>
				<h3 id="adminmessage">Contact an administrator if you think this is an error</h3>
			</div>
		);
	}
}
