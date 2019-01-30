import {Component, h} from "preact";
import {Link} from "preact-router";

import {GuildListNavState} from "./state";

import Gear from "./gear";

export default class GuildNav extends Component<{}, GuildListNavState> {

    constructor(props, state) {
        super(props, state)
        
        this.setState({
            guilds: [
                {guildName: "The Gearbox", guildID: 39309044394302, guildIcon: "SomeURLHere"},
                {guildName: "The Other Gearbox", guildID: 30943043023434, guildIcon: "AnotherURL"},
                {guildName: "Blob Emotes 3", guildID: 3930349343333, guildIcon: "OneLastURL"}
            ]
        })
        
    }
    
    render() {
        return (
            <div class="guild-nav">
                <ul>
                {   
                    (this.state.guilds != null) ? this.state.guilds.map((guild) => <div class="guildItem">
                        <Gear image={guild.guildIcon} size={150}></Gear>
						<li><Link href={"/dashboard/guild/"+ guild.guildID} activeClassName={"active"}>{guild.guildName}</Link></li>
					</div>): <div class="noGuildsFoundMessage">No guilds currently avaliable</div>
                }  
                </ul>
            </div>

        );
    }

}