import {h, Component} from "preact";

import "../style/styles.css";

export default class Home extends Component<{}, {}> {
	render() {
		return <div class="home">
			<h1>Home</h1>
			<p>This is the homepage</p>
		</div>;
	}
}
