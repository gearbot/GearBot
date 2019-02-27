import {Component, h} from "preact";

export default class Home extends Component<{}, {}> {
	render() {
		return <div class="home">
			<h1>Welcome</h1>
			<p>GearBot will help you to keep the gears turning on your server, and while that kind of extends to this website, it is still very much WIP. The documentation section works completely, but the dashboard is still being worked on.</p>

			<h2>How to add and use GearBot</h2>
			<p>Check out <a href="docs/guides/adding_gearbot">the guide on adding GearBot</a> for adding the bot to your server. There is an entire section in the docs as well on setting up different parts of the bot.</p>

			<h2>Support</h2>
			<p>Check out <a href="docs/">the docs</a>: they have a lot of information and should help you in most cases. You can also drop by the <a href="https://discord.gg/S4DBxtC">support server</a> for questions, stay up to date on the updates and more.</p>

			<h2>Contributing</h2>
			<p>GearBot is fully open source (as well as this site) and contributions are more than welcome. Feel free to drop by on the <a href="https://discord.gg/S4DBxtC">support server</a> to talk about what you want to do. Or you can take on of the existing tickets on the <a href="https://github.com/AEnterprise/GearBot">GitHub</a>. Please do leave a comment first asking about to so I know someone is working on it to avoid double work being done.</p>
		</div>;
	}
}
