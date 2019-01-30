export interface GearState {
	rotation: number;
	spinning: boolean;
}

export interface DashboardState {
	currentUrl: string;
}

export interface HeaderState {

}

export interface GuildListNavState {
	guilds: GuildListObject[]
}

export interface GuildListObject {
	guildName: string,
	guildID: number,
	guildIcon: string,
}

export interface DocState {
	markdown: string
}
