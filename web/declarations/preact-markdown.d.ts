import { VNode } from 'preact';

declare var p: PreactMarkdown;
export default p;


interface PreactMarkdown {
    (request: string, opts?: object): VNode;
    (request: object, opts?: object): VNode;
}
