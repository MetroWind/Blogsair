$(function()
{
    var AllPars = $("p");
    var ImgPars = AllPars.has("a").add(AllPars.has("img"));

    ImgPars.each(function(idx, element)
    {
        if($(this).text() === "")
        // This is p that only contains img.
        {
            $(this).addClass("ImgWrapper");
        }
    });
});
