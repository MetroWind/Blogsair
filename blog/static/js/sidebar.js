$(function()
{
    var Sidebar = $("aside#Sidebar");
    var MainText = $("div#Wrapper");
    var Header = $("header");

    Sidebar.css("float", "none");
    Sidebar.css("position", "absolute");

    var PosMainText = MainText.offset();
    var PosSidebar = {left: PosMainText.left + MainText.outerWidth() + 30,
                      top: Header.outerHeight(true) + PosMainText.top};

    Sidebar.offset(PosSidebar);
});
